"""Small shared HTTP contract for the native installation; decimals stay exact on disk."""

import math
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal, Self
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

Market = Literal["tradingview", "tsetmc"]
Number = Annotated[Decimal, Field(allow_inf_nan=False, max_digits=40, decimal_places=18)]


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    market: Market
    symbol: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_:.-]+$")
    interval: Literal["1m", "5m", "15m", "1d", "quote"]
    time: int = Field(ge=0, le=32503680000, strict=True)
    received_at: AwareDatetime
    event_at: AwareDatetime | None = None
    open: Number | None = None
    close: Number | None = None
    high: Number | None = None
    low: Number | None = None
    last: Number | None = None
    bid: Number | None = None
    ask: Number | None = None
    official_close: Number | None = None
    count: int | None = Field(default=None, ge=0, le=2**63 - 1, strict=True)
    volume: Number | None = Field(default=None, ge=0)
    value: Number | None = Field(default=None, ge=0)
    status: Literal["realtime", "delayed", "unknown", "end_of_day", "indicative"] = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "open",
        "close",
        "high",
        "low",
        "last",
        "bid",
        "ask",
        "official_close",
        "volume",
        "value",
        mode="before",
    )
    @classmethod
    def exact_numbers(cls, value: Any) -> Any:
        if isinstance(value, (float, bool)):
            raise ValueError("send prices as decimal strings or integers")
        return value

    @field_validator("received_at", "event_at")
    @classmethod
    def utc(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(UTC) if value else None

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.interval == "quote":
            if self.time != 0 or all(
                v is None for v in (self.last, self.bid, self.ask, self.official_close)
            ):
                raise ValueError("quote requires time=0 and an observed price")
        else:
            step = {"1m": 60, "5m": 300, "15m": 900, "1d": 86400}[self.interval]
            if self.market == "tradingview" and self.interval == "1d":
                step = 60  # Preserve provider session timestamps, not UTC day aggregation.
            if self.time % step:
                raise ValueError("bar timestamp must align to its UTC interval")
            if self.high is not None and self.low is not None and self.high < self.low:
                raise ValueError("high is below low")
            if (
                (self.market == "tradingview" or self.interval != "1d")
                and self.high is not None
                and self.low is not None
            ):
                if any(
                    v is not None and not self.low <= v <= self.high
                    for v in (self.open, self.close)
                ):
                    raise ValueError("OHLC is outside the trading range")
        if self.market == "tsetmc" and (
            not self.symbol.isascii()
            or not self.symbol.isdigit()
            or self.interval not in {"1m", "1d", "quote"}
        ):
            raise ValueError("TSETMC requires insCode and 1m/1d/quote observations")
        if self.market == "tsetmc":
            if len(self.symbol) > 30:
                raise ValueError("TSETMC insCode exceeds 30 digits")
            measurements = (
                self.open,
                self.close,
                self.high,
                self.low,
                self.last,
                self.bid,
                self.ask,
                self.official_close,
                self.volume,
                self.value,
            )
            if any(v is not None and v < 0 for v in measurements):
                raise ValueError("TSETMC measurements must be nonnegative")
            if self.count is None and all(v is None for v in measurements):
                raise ValueError("TSETMC record contains no observed measurements")
            if self.high is not None and self.low is not None:
                if self.high < self.low:
                    raise ValueError("high is below low")
                if self.low > 0 and self.count != 0 and self.volume != 0:
                    if any(
                        v is not None and not self.low <= v <= self.high
                        for v in (self.open, self.last)
                    ):
                        raise ValueError("TSETMC open/last is outside the executed trading range")
            if self.interval == "1d" and self.close is not None and self.official_close is not None:
                if self.close != self.official_close:
                    raise ValueError(
                        "TSETMC daily close must equal official_close when both supplied"
                    )
            if self.event_at is not None and self.event_at > self.received_at + timedelta(
                minutes=5
            ):
                raise ValueError(
                    "TSETMC source clock exceeds receive time by more than five minutes"
                )
        return self


class IntradaySnapshot(BaseModel):
    """A reconciled TSETMC day replacement or a provisional upsert-only snapshot."""

    model_config = ConfigDict(extra="forbid")
    market: Literal["tsetmc"] = "tsetmc"
    symbol: str = Field(pattern=r"^[0-9]{1,30}$")
    interval: Literal["1m"] = "1m"
    trading_date: date = Field(ge=date(1970, 1, 1), le=date(2999, 12, 30))
    received_at: AwareDatetime
    reconciled: bool = Field(default=True, strict=True)

    def bounds(self) -> tuple[int, int]:
        zone = ZoneInfo("Asia/Tehran")
        start = datetime.combine(self.trading_date, time(), zone)
        return int(start.timestamp()), int((start + timedelta(days=1)).timestamp())


class Batch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_id: UUID
    observations: list[Observation] = Field(max_length=5000)
    snapshot: IntradaySnapshot | None = None

    @model_validator(mode="after")
    def unique(self) -> Self:
        if self.snapshot:
            s = self.snapshot
            if not s.reconciled and not self.observations:
                raise ValueError("an empty intraday snapshot must be reconciled")
            start, end = s.bounds()
            if start < 0 or end > 32503680000 or start > s.received_at.timestamp():
                raise ValueError("invalid snapshot trading date")
            if any(
                (o.market, o.symbol, o.interval) != (s.market, s.symbol, s.interval)
                or not start <= o.time < end
                or o.received_at != s.received_at
                or (not s.reconciled and o.metadata.get("finality") != "provisional")
                or o.time > s.received_at.timestamp() + 300
                or any(
                    v is None for v in (o.open, o.close, o.high, o.low, o.count, o.volume, o.value)
                )
                or o.count == 0
                or o.volume == 0
                or (o.low is not None and o.low <= 0)
                for o in self.observations
            ):
                raise ValueError("snapshot requires complete minute candles within one trade day")
        elif not self.observations:
            raise ValueError("empty batch requires an intraday snapshot")
        if not self.snapshot and any(
            o.market == "tsetmc" and o.interval == "1m" for o in self.observations
        ):
            raise ValueError("TSETMC minute bars require trade-day snapshot scope")
        keys = [(o.market, o.symbol, o.interval, o.time) for o in self.observations]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate observation identity in batch")
        return self


def float64(value: Any) -> float:
    number = Decimal(str(value))
    result = float(number)
    if not math.isfinite(result) or (result == 0 and number != 0):
        raise ValueError("value cannot be represented by dashboard float64")
    return result
