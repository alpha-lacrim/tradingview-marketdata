"""Freeze the native 100-feed selection from captured TradingView scanner responses.

Offline only: never rotates a running collector's instruments or changes old registries.
"""

import argparse
import copy
import json
from decimal import Decimal
from pathlib import Path

from marketdata.domain import RegistryEntry
from marketdata.registry import Registry


def prepare(ranking: dict, directory: dict, existing: list[dict]) -> list[dict]:
    catalog = {r["s"] for r in directory["data"]}
    known = {e["mappings"][0]["provider_symbol"]: e for e in existing}
    eligible = []
    for row in ranking["response"]["data"]:
        name, exchange, kind, currency, base, volume = row["d"][:6]
        if exchange != "BINANCE" or kind != "spot" or currency != "USDT":
            continue
        if row["s"] != f"BINANCE:{name}" or not base:
            raise ValueError("inconsistent Binance identity")
        if volume is None:
            continue
        amount = Decimal(str(volume))
        if not amount.is_finite():
            raise ValueError("non-finite ranking volume")
        if amount > 0:
            eligible.append((amount, row["s"], base))
    eligible.sort(key=lambda item: (-item[0], item[1]))
    if len(eligible) < 50 or len({r[1] for r in eligible}) != len(eligible):
        raise ValueError("need at least 50 distinct positive-volume Binance pairs")
    entries = []
    for rank, (_, symbol, base) in enumerate(eligible[:50], 1):
        entry = copy.deepcopy(known.get(symbol))
        if entry is None:
            entry = dict(
                instrument=dict(
                    canonical_symbol="CRYPTO:" + symbol,
                    display_name=symbol,
                    asset_class="crypto",
                    instrument_type="spot",
                    exchange="BINANCE",
                    currency="USDT",
                    base_asset=base,
                    quote_asset="USDT",
                ),
                mappings=[
                    dict(
                        provider="tradingview_guest",
                        provider_symbol=symbol,
                        realtime_status="unknown",
                        metadata=dict(source_type="spot"),
                    )
                ],
            )
        entry["mappings"][0]["metadata"].update(
            ranking_basis="TradingView 24h_vol|5 (USD), Binance spot USDT pairs",
            ranking_at=ranking["captured_at"],
            ranking_position=rank,
        )
        entries.append(entry)
    pairs = (
        "EURUSD GBPUSD USDJPY USDCHF AUDUSD USDCAD NZDUSD EURGBP EURJPY EURCHF "
        "EURAUD EURCAD EURNZD GBPJPY GBPCHF GBPAUD GBPCAD GBPNZD AUDJPY CADJPY CHFJPY"
    ).split()
    selected = [f"{broker}:{pair}" for broker in ("OANDA", "FX") for pair in pairs]
    selected += [
        "OANDA:XAUUSD",
        "OANDA:XAGUSD",
        "OANDA:XPTUSD",
        "OANDA:XPDUSD",
        "FX:XAUUSD",
        "OANDA:WTICOUSD",
        "OANDA:BCOUSD",
        "OANDA:NATGASUSD",
    ]
    for symbol in selected:
        if symbol not in known:
            raise ValueError("missing directory identity or qualified mapping: " + symbol)
        entry = copy.deepcopy(known[symbol])
        entry["mappings"][0]["metadata"]["current_directory_present"] = symbol in catalog
        entries.append(entry)
    Registry([RegistryEntry.model_validate(e) for e in entries])
    assert len(entries) == 100
    return entries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ranking", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("config/instruments.tradingview-native100.json")
    )
    args = parser.parse_args()
    known = json.loads(
        Path("config/instruments.tradingview-business-candidates.json").read_text("utf-8")
    )
    entries = prepare(
        json.loads(args.ranking.read_text("utf-8")),
        json.loads(args.directory.read_text("utf-8")),
        known,
    )
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} source entries to {args.output}")
