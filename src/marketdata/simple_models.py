"""Small shared HTTP contract for the native installation; decimals stay exact on disk."""

import math
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

Market = Literal["tradingview", "tsetmc"]
Number = Annotated[Decimal, Field(allow_inf_nan=False, max_digits=40, decimal_places=18)]


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    market: Market
    symbol: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_:.-]+$")
    interval: Literal["1m", "1d", "quote"]
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
            step = 60 if self.interval == "1m" else 86400
            if self.time % step:
                raise ValueError("bar timestamp must align to its UTC interval")
            if self.high is not None and self.low is not None and self.high < self.low:
                raise ValueError("high is below low")
            if self.market == "tradingview" and self.high is not None and self.low is not None:
                if any(
                    v is not None and not self.low <= v <= self.high
                    for v in (self.open, self.close)
                ):
                    raise ValueError("OHLC is outside the trading range")
        if self.market == "tsetmc" and (
            not self.symbol.isascii() or not self.symbol.isdigit() or self.interval == "1m"
        ):
            raise ValueError("TSETMC requires native insCode and daily history")
        if self.market == "tradingview" and self.interval == "1d":
            raise ValueError("upload TradingView native 1m bars; daily bars are queried aggregates")
        return self


class Batch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_id: UUID
    observations: list[Observation] = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def unique(self) -> Self:
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
