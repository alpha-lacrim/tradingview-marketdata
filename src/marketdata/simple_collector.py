"""Native TradingView candles and quote snapshots -> one company HTTP API."""

import argparse
import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import httpx
from websockets.exceptions import ConnectionClosed, InvalidMessage, InvalidStatus

from marketdata.candles import MarketCandle
from marketdata.config import MAX_HISTORY_MINUTES, Settings
from marketdata.domain import Tick
from marketdata.observability import Metrics
from marketdata.providers.base import PermanentConnectionError, PermanentProviderError, Subscription
from marketdata.providers.tradingview import TradingViewGuestProvider
from marketdata.providers.tradingview_candles import TradingViewCandleProvider
from marketdata.registry import Registry
from marketdata.simple_delivery import PendingUpload, retry_delay, single_instance


def transport_detail(error: Exception) -> str:
    """Diagnostic codes only; never log response bodies, headers or credentials."""
    detail = type(error).__name__
    if isinstance(error, InvalidStatus):
        detail += f" HTTP {error.response.status_code}"
    if isinstance(error, ConnectionClosed):
        detail += f" received_code={getattr(error.rcvd, 'code', None)}"
        detail += f" sent_code={getattr(error.sent, 'code', None)}"
    if error.__cause__ is not None:
        detail += f" cause={type(error.__cause__).__name__}"
    return detail


def transport_delay(error: Exception, minimum: float) -> float:
    if isinstance(error, InvalidStatus):
        return retry_delay(error.response.headers.get("Retry-After"), minimum)
    return minimum


def candle_record(bar: MarketCandle, pair: Subscription) -> dict[str, Any]:
    return dict(
        market="tradingview",
        symbol=bar.provider_symbol,
        interval=bar.interval,
        time=int(bar.bucket_start.timestamp()),
        received_at=bar.received_timestamp,
        open=bar.open,
        close=bar.close,
        high=bar.high,
        low=bar.low,
        volume=bar.volume,
        status=bar.realtime_status.value,
        metadata={
            **bar.metadata,
            "canonical_symbol": bar.canonical_symbol,
            "instrument_type": pair[0].instrument_type.value,
            "currency": pair[0].currency,
            "exchange": pair[0].exchange,
        },
    )


def quote_record(tick: Tick) -> dict[str, Any]:
    return dict(
        market="tradingview",
        symbol=tick.provider_symbol,
        interval="quote",
        time=0,
        received_at=tick.received_timestamp,
        event_at=tick.event_timestamp,
        last=tick.last,
        bid=tick.bid,
        ask=tick.ask,
        status=tick.realtime_status.value,
        metadata={
            **tick.metadata,
            "canonical_symbol": tick.canonical_symbol,
            "instrument_type": tick.instrument_type.value,
            "exchange": tick.exchange,
        },
    )


async def run(args: argparse.Namespace) -> None:
    pairs = Registry.load(args.registry).subscriptions("tradingview_guest")
    if not 1 <= len(pairs) <= 100:
        raise ValueError("registry must contain 1..100 TradingView sources")
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        candle_backfill_minutes=args.history_minutes,
        tradingview_candle_concurrency=2,
        candle_request_timeout_seconds=30,
    )
    metrics = Metrics()
    headers = (
        {"Authorization": "Bearer " + os.environ["SIMPLE_UPLOAD_TOKEN"]}
        if os.getenv("SIMPLE_UPLOAD_TOKEN")
        else {}
    )
    async with httpx.AsyncClient(timeout=30, headers=headers, trust_env=False) as http:
        bars_pending = PendingUpload(args.api_url, args.state_dir / "history.json", http)
        quotes_pending = PendingUpload(args.api_url, args.state_dir / "latest.json", http)
        recent: dict[str, Tick] = {}

        async def candles() -> None:
            success_by_interval: dict[str, dict[str, datetime]] = {}
            full_by_interval: dict[str, dict[str, datetime]] = {}
            backoff = 60.0
            concurrency = settings.tradingview_candle_concurrency
            while True:
                await bars_pending.drain()
                intervals: list[Literal["1m", "5m", "15m", "1d"]] = getattr(
                    args, "intervals", ["1m"]
                )
                cycle_delay = 60.0
                for interval in dict.fromkeys(intervals):
                    step = {"1m": 1, "5m": 5, "15m": 15, "1d": 1440}[interval]
                    last_success = success_by_interval.setdefault(interval, {})
                    last_full = full_by_interval.setdefault(interval, {})
                    delay = backoff
                    provider = TradingViewCandleProvider(settings, metrics, interval=interval)
                    provider.effective_concurrency = concurrency
                    await provider.subscribe(pairs)
                    try:
                        await provider.connect()
                        end = (datetime.now(UTC) - timedelta(seconds=3)).replace(
                            second=0, microsecond=0
                        )
                        jobs = []
                        for pair in pairs:
                            symbol = pair[0].canonical_symbol
                            full = (
                                symbol not in last_full
                                or (end - last_full[symbol]).total_seconds() >= 3600
                            )
                            start = end - timedelta(minutes=args.history_minutes * step)
                            if not full and symbol in last_success:
                                start = max(
                                    start, last_success[symbol] - timedelta(minutes=30 * step)
                                )
                            jobs.append(
                                (
                                    pair,
                                    start,
                                    end,
                                    int((end - start).total_seconds() // (60 * step)) + 1,
                                )
                            )
                        failed = empty = delivered = 0
                        # Bound recovery memory: do not retain 5000 bars for all 100 sources.
                        for offset in range(0, len(jobs), 10):
                            batch = jobs[offset : offset + 10]
                            results = await provider.fetch_many(batch)
                            for pair, _, _, _ in batch:
                                symbol = pair[0].canonical_symbol
                                bars = results[symbol]
                                if isinstance(bars, PermanentConnectionError):
                                    raise bars
                                if isinstance(bars, Exception):
                                    failed += 1
                                    print(
                                        f"history {pair[1].provider_symbol}: "
                                        f"{transport_detail(bars)}",
                                        flush=True,
                                    )
                                    delay = max(delay, transport_delay(bars, backoff))
                                    continue
                                if not bars:
                                    empty += 1
                                delivered += len(bars)
                                for offset in range(0, len(bars), 500):
                                    bars_pending.stage(
                                        [
                                            candle_record(b, pair)
                                            for b in bars[offset : offset + 500]
                                        ]
                                    )
                                    await bars_pending.drain()
                                last_success[symbol] = end
                                if (
                                    symbol not in last_full
                                    or (end - last_full[symbol]).total_seconds() >= 3600
                                ):
                                    last_full[symbol] = end
                        print(
                            f"history {interval} cycle: {len(pairs) - failed} requests succeeded, "
                            f"{failed} failed; "
                            f"{delivered} bars delivered, {empty} empty results",
                            flush=True,
                        )
                        if not failed:
                            backoff = delay = 60.0
                        else:
                            backoff = min(backoff * 2, 300)
                        if args.once and failed:
                            raise RuntimeError(f"history failed for {failed} sources")
                    except PermanentProviderError:
                        raise
                    except (
                        OSError,
                        TimeoutError,
                        ConnectionClosed,
                        InvalidMessage,
                        InvalidStatus,
                    ) as error:
                        delay = transport_delay(error, backoff)
                        backoff = min(backoff * 2, 300)
                        print(
                            f"history transport: {transport_detail(error)}; retry in {delay:g}s",
                            flush=True,
                        )
                        if args.once:
                            raise
                    finally:
                        concurrency = min(concurrency, provider.effective_concurrency)
                        await provider.disconnect()
                    cycle_delay = max(cycle_delay, delay)
                if args.once:
                    return
                await asyncio.sleep(cycle_delay)

        async def quotes() -> None:
            backoff = 60.0
            while True:
                delay = backoff
                provider = TradingViewGuestProvider(settings, metrics)
                await provider.subscribe(pairs)
                try:
                    await provider.connect()
                    async for tick in provider.stream_ticks():
                        # Keep one latest snapshot per configured source, not a tick archive.
                        recent[tick.provider_symbol] = tick
                        backoff = delay = 60.0
                except PermanentProviderError:
                    raise
                except (
                    OSError,
                    TimeoutError,
                    ConnectionClosed,
                    InvalidMessage,
                    InvalidStatus,
                ) as error:
                    delay = transport_delay(error, backoff)
                    print(
                        f"quote transport: {transport_detail(error)}; reconnect in {delay:g}s",
                        flush=True,
                    )
                finally:
                    await provider.disconnect()
                await asyncio.sleep(delay)
                backoff = min(backoff * 2, 300)

        async def publish_quotes() -> None:
            while True:
                await quotes_pending.drain()
                if recent:
                    snapshot = list(recent.values())
                    recent.clear()
                    quotes_pending.stage([quote_record(t) for t in snapshot])
                    await quotes_pending.drain()
                await asyncio.sleep(5)

        if args.once:
            await candles()
        else:
            async with asyncio.TaskGroup() as group:
                group.create_task(candles())
                group.create_task(quotes())
                group.create_task(publish_quotes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=os.getenv("COMPANY_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("config/instruments.tradingview-native100.json"),
    )
    parser.add_argument("--state-dir", type=Path, default=Path(".local/simple-tradingview"))
    parser.add_argument(
        "--history-bars",
        "--history-minutes",
        dest="history_minutes",
        type=int,
        default=MAX_HISTORY_MINUTES,
        help="recovery bars per interval (30..4999); old flag remains an alias",
    )
    parser.add_argument(
        "--intervals",
        nargs="+",
        choices=["1m", "5m", "15m", "1d"],
        default=["1m", "5m", "15m", "1d"],
    )
    parser.add_argument("--once", action="store_true", help="upload one history cycle and exit")
    args = parser.parse_args()
    if not 30 <= args.history_minutes <= MAX_HISTORY_MINUTES:
        parser.error(f"history-minutes must be 30..{MAX_HISTORY_MINUTES}")
    with single_instance(args.state_dir):
        try:
            asyncio.run(run(args))
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
