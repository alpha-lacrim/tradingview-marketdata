"""Canonical tsetmc.v1 financial validation and hashing."""

import hashlib
import json
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID


def validate_measurements(values: dict[str, Decimal | None], trade_count: int | None) -> None:
    if trade_count is not None and (type(trade_count) is not int or trade_count < 0):
        raise ValueError("zTotTran must be a nonnegative integer or null")
    for name, value in values.items():
        if value is not None and (
            not isinstance(value, Decimal) or not value.is_finite() or value < 0
        ):
            raise ValueError(f"{name} must be a finite nonnegative Decimal or null")
    high, low = values["high"], values["low"]
    if high is not None and low is not None:
        if high < low:
            raise ValueError("priceMax is lower than priceMin")
        if low > 0 and trade_count != 0 and values["traded_volume"] != 0:
            for name in ("opening_price", "last_traded_price"):
                value = values[name]
                if value is not None and not low <= value <= high:
                    raise ValueError(f"{name} is outside the executed trading range")
    # The official close is not constrained to the executed-trade range.


def decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return decimal_text(value)
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_safe(item) for item in value]
    return value


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        json_safe(value), sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(encoded.encode()).hexdigest()
