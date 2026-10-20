"""Independent destination validation of the published tsetmc.v1 contract.

The bundled schema is frozen public specification, not a dependency on the source
collector. Financial, record and exact-byte hashes deliberately use different inputs.
"""

import hashlib
import json
import re
from datetime import datetime, time
from decimal import Decimal
from functools import lru_cache
from importlib.resources import files
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

MAX_INT64 = 2**63 - 1
STREAMS = ("tsetmc_daily", "tsetmc_current", "tsetmc_coverage", "tsetmc_status")
MEASUREMENTS = (
    "previous_close",
    "opening_price",
    "last_traded_price",
    "high",
    "low",
    "official_close",
    "trade_count",
    "traded_volume",
    "traded_value",
)
POSITIONS = {
    "source_position",
    "state_version",
    "financial_revision",
    "local_snapshot_id",
    "local_observation_id",
    "local_revision_id",
    "local_decision_id",
    "stored_state_version",
    "source_fence",
}


class TsetmcError(ValueError):
    """Safe error diagnostics never contain input values."""

    def __init__(self, code: str, status: int = 422, indexes: list[int] | None = None):
        super().__init__(code)
        self.code, self.status, self.indexes = code, status, indexes or []


def canonical(value: Any, *, ascii_only: bool = False) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=ascii_only, allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def record_hash(record: dict[str, Any]) -> str:
    return digest({k: record[k] for k in ("kind", "event_type", "observation")})


def financial_hash(observation: dict[str, Any], values: dict[str, Any] | None = None) -> str:
    measurements = values if values is not None else observation["measurements"]
    state = dict(ins_code=observation["ins_code"], **measurements)
    state["trade_count"] = (
        int(measurements["trade_count"]) if measurements["trade_count"] is not None else None
    )
    if "trading_date" in observation:
        state["trading_date"] = observation["trading_date"]
    else:
        state.update(
            instrument_state=observation["instrument_state"],
            instrument_state_title=observation["instrument_state_title"],
        )
    return hashlib.sha256(canonical(state, ascii_only=True)).hexdigest()


def instrument_id(code: str) -> UUID:
    if not isinstance(code, str) or re.fullmatch(r"[1-9][0-9]{0,19}", code) is None:
        raise TsetmcError("source_identity_conflict", 409)
    return uuid5(NAMESPACE_URL, "marketdata:instrument:TSETMC:" + code)


@lru_cache
def schema() -> dict[str, Any]:
    return dict(
        json.loads(files("marketdata").joinpath("contracts/tsetmc.v1.schema.json").read_text())
    )


@lru_cache
def validator(definition: str) -> Draft202012Validator:
    return Draft202012Validator(
        {"$defs": schema()["$defs"], "$ref": "#/$defs/" + definition},
        format_checker=FormatChecker(),
    )


def decode(payload: bytes) -> dict[str, Any]:
    if len(payload) > 2 * 1024 * 1024:
        raise TsetmcError("body_limit_exceeded", 413)

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = dict(pairs)
        if len(result) != len(pairs):
            raise TsetmcError("invalid_batch")
        return result

    def reject(_: str) -> Any:
        raise TsetmcError("invalid_batch")

    try:
        value = json.loads(
            payload, object_pairs_hook=unique, parse_float=reject, parse_constant=reject
        )
        if not isinstance(value, dict):
            raise TsetmcError("invalid_batch")
        return value
    except (UnicodeError, ValueError, RecursionError):
        raise TsetmcError("invalid_batch") from None


def measurements_valid(values: dict[str, Any]) -> None:
    for key, value in values.items():
        pattern = (
            r"(?:0|[1-9][0-9]*)"
            if key == "trade_count"
            else (r"(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?")
        )
        if value is not None and re.fullmatch(pattern, value) is None:
            raise TsetmcError("invalid_batch")
    numbers = {k: Decimal(v) if v is not None else None for k, v in values.items()}
    high, low = numbers["high"], numbers["low"]
    if high is not None and low is not None:
        if high < low:
            raise TsetmcError("invalid_batch")
        if low > 0 and numbers["trade_count"] != 0 and numbers["traded_volume"] != 0:
            for name in ("opening_price", "last_traded_price"):
                value = numbers[name]
                if value is not None and not low <= value <= high:
                    raise TsetmcError("invalid_batch")


def validate(value: dict[str, Any], definition: str) -> None:
    try:
        validator(definition).validate(value)
    except (ValidationError, RecursionError):
        raise TsetmcError(
            "invalid_reconciliation" if definition == "ReconcileRequest" else "invalid_batch"
        ) from None

    def walk(item: Any) -> None:
        if isinstance(item, str):
            try:
                item.encode("utf-8")
            except UnicodeEncodeError:
                raise TsetmcError("invalid_batch") from None
        if isinstance(item, float):
            raise TsetmcError("invalid_batch")
        if isinstance(item, list):
            for child in item:
                walk(child)
        if not isinstance(item, dict):
            return
        for key, child in item.items():
            if child is not None and key in POSITIONS:
                if re.fullmatch(r"[1-9][0-9]{0,18}", child) is None or not (
                    0 < int(child) <= MAX_INT64
                ):
                    raise TsetmcError("invalid_batch")
            if key == "evidence_observation_ids" and any(
                re.fullmatch(r"[1-9][0-9]{0,18}", local_id) is None
                or not 0 < int(local_id) <= MAX_INT64
                for local_id in child
            ):
                raise TsetmcError("invalid_finalization")
            if key in {"protocol_version", "ownership_generation", "session_generation", "limit"}:
                if type(child) is not int:
                    raise TsetmcError("invalid_batch")
            # UUID format checking alone admits noncanonical spelling.
            if (
                child is not None
                and key
                in {
                    "producer_id",
                    "session_id",
                    "batch_id",
                    "source_epoch",
                    "instrument_id",
                    "observation_id",
                    "review_id",
                    "seed_id",
                    "destination_id",
                }
                and str(UUID(child)) != child
            ):
                raise TsetmcError("invalid_batch")
            walk(child)
        if item.get("provider") == "tsetmc":
            code = item["ins_code"]
            if (item["instrument_id"], item["canonical_symbol"], item["provider_symbol"]) != (
                str(instrument_id(code)),
                "TSETMC:" + code,
                code,
            ):
                raise TsetmcError("source_identity_conflict", 409)
        if "measurements" in item:
            measurements_valid(item["measurements"])
            if financial_hash(item) != item["financial_hash"]:
                raise TsetmcError("financial_hash_mismatch")
        evidence = item.get("revision_evidence")
        if evidence:
            if int(evidence["financial_revision"]) < 2:
                raise TsetmcError("invalid_batch")
            for side in ("old", "new"):
                measurements_valid(evidence[side + "_measurements"])
                if (
                    financial_hash(item, evidence[side + "_measurements"])
                    != evidence[side + "_financial_hash"]
                ):
                    raise TsetmcError("financial_hash_mismatch")
            if evidence["old_financial_hash"] == evidence["new_financial_hash"]:
                raise TsetmcError("invalid_batch")
            if "financial_hash" in item and (
                item["financial_hash"] != evidence["new_financial_hash"]
                or item["financial_revision"] != evidence["financial_revision"]
                or item["measurements"] != evidence["new_measurements"]
            ):
                raise TsetmcError("invalid_batch")
        if "local_finalization" in item and "review" in item:
            review = item["review"]
            finalized = item["local_finalization"] == "operator_finalized"
            if finalized and (not review or review["action"] != "confirm"):
                raise TsetmcError("invalid_finalization")
            if review:
                if review["reviewed_financial_hash"] != item["financial_hash"] or (
                    (review["action"] == "confirm") != finalized
                ):
                    raise TsetmcError("invalid_finalization")
                if (
                    review["action"] == "confirm"
                    and len(set(review["evidence_observation_ids"])) != 2
                ):
                    raise TsetmcError("invalid_finalization")
        if item.get("source_time") is not None:
            try:
                time.fromisoformat(item["source_time"])
            except ValueError:
                raise TsetmcError("invalid_batch") from None
            if re.fullmatch(r"[0-9]{2}:[0-9]{2}:[0-9]{2}", item["source_time"]) is None:
                raise TsetmcError("invalid_batch")
        if "source_reported_at" in item and item["source_reported_at"] is not None:
            if item["source_date"] is None or item["source_time"] is None:
                raise TsetmcError("invalid_batch")
            local = datetime.fromisoformat(item["source_date"] + "T" + item["source_time"]).replace(
                tzinfo=ZoneInfo("Asia/Tehran")
            )
            if local != datetime.fromisoformat(item["source_reported_at"]):
                raise TsetmcError("invalid_batch")
        if "expires_at" in item and "captured_at" in item:
            ttl = (
                datetime.fromisoformat(item["expires_at"])
                - datetime.fromisoformat(item["captured_at"])
            ).total_seconds()
            if not 0 < ttl <= 120:
                raise TsetmcError("invalid_batch")
        if "coverage_rows" in item:
            days = [r["trading_date"] for r in item["coverage_rows"]]
            if len(set(days)) != len(days) or any(
                not item["from_date"] <= d <= item["through_date"] for d in days
            ):
                raise TsetmcError("invalid_batch")
        if "from_date" in item and item["from_date"] > item["through_date"]:
            raise TsetmcError(
                "invalid_reconciliation" if definition == "ReconcileRequest" else "invalid_batch"
            )

    walk(value)
    if definition == "Batch":
        positions = [int(r["source_position"]) for r in value["records"]]
        if positions != sorted(set(positions)):
            raise TsetmcError("invalid_batch")
        for index, record in enumerate(value["records"]):
            try:
                observation = record["observation"]
                if observation["instrument_id"] != value["instrument_id"] or record[
                    "observation_id"
                ] != str(
                    uuid5(
                        UUID(value["source_epoch"]),
                        value["stream"] + ":" + record["source_position"],
                    )
                ):
                    raise TsetmcError("source_identity_conflict", 409)
                event = record["event_type"]
                if record["kind"] == "daily":
                    if event == "daily.corrected" and (
                        not observation["revision_evidence"]
                        or observation["local_finalization"] != "source_unverified"
                    ):
                        raise TsetmcError("invalid_finalization")
                    if event in {"daily.review_confirmed", "daily.review_revoked"}:
                        action = "confirm" if event == "daily.review_confirmed" else "revoke"
                        if not observation["review"] or observation["review"]["action"] != action:
                            raise TsetmcError("invalid_finalization")
                        if (
                            action == "confirm"
                            and observation["reconciliation"]["open_quarantine_count"]
                        ):
                            raise TsetmcError("invalid_finalization")
                if record["kind"] == "current":
                    if observation["state_version"] != record["source_position"]:
                        raise TsetmcError("invalid_batch")
                    if (
                        observation["accepted_decision"] == "explicit_same_time_correction"
                        and not observation["correction_reason_sha256"]
                    ):
                        raise TsetmcError("invalid_batch")
                    if observation["accepted_decision"] == "repeated_state" and (
                        event not in {"current.seed", "current.resnapshot"}
                        or observation["financial_change"]
                    ):
                        raise TsetmcError("invalid_batch")
            except TsetmcError as error:
                raise TsetmcError(error.code, error.status, [index]) from None
    if definition == "ReconcileRequest":
        if str(instrument_id(value["ins_code"])) != value["instrument_id"]:
            raise TsetmcError("source_identity_conflict", 409)
        keys = value.get("keys", [])
        if len({(k["stream"], k["trading_date"]) for k in keys}) != len(keys) or any(
            (k["trading_date"] is not None) != (k["stream"] in {"tsetmc_daily", "tsetmc_coverage"})
            for k in keys
        ):
            raise TsetmcError("invalid_reconciliation")
