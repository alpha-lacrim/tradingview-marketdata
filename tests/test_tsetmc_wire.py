"""Public synthetic contract only; independent hashes and hostile wire inputs."""

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from marketdata.tsetmc_wire import (
    TsetmcError,
    canonical,
    decode,
    digest,
    financial_hash,
    record_hash,
    schema,
    validate,
)

DIRECTORY = Path(__file__).parent / "fixtures/tsetmc_v1"
MANIFEST = json.loads((DIRECTORY / "examples-manifest.json").read_text())


def example(name):
    return decode((DIRECTORY / "examples" / (name + ".json")).read_bytes())


@pytest.mark.parametrize("field", ["official_close", "trade_count"])
@pytest.mark.parametrize(
    "lexeme",
    [
        "112\n",
        "112\r",
        "112\t",
        " 112",
        "112 ",
        "112\u00a0",
        "112\u2028",
        "012",
        "112.0",
        "1e2",
        "+112",
        "-0",
    ],
)
def test_financial_strings_require_complete_canonical_spelling(field, lexeme):
    value = example("daily.request")
    observation = value["records"][0]["observation"]
    observation["measurements"][field] = lexeme
    # Recomputed hashes must never make a noncanonical representation acceptable.
    try:
        observation["financial_hash"] = financial_hash(observation)
    except ValueError:
        pass  # Fractional/exponent count strings cannot even form a protocol financial hash.
    with pytest.raises(TsetmcError):
        validate(value, "Batch")


@pytest.mark.parametrize("side", ["old", "new"])
def test_revision_measurements_also_reject_trailing_newline(side):
    value = example("revision-seed.request")
    observation = value["records"][0]["observation"]
    evidence = observation["revision_evidence"]
    evidence[side + "_measurements"]["official_close"] += "\n"
    evidence[side + "_financial_hash"] = financial_hash(
        observation, evidence[side + "_measurements"]
    )
    with pytest.raises(TsetmcError):
        validate(value, "Batch")


@pytest.mark.parametrize("clock", ["99:99:99", "24:00:00", "12:60:00", "12:00:60", "12:00:00\n"])
def test_local_clock_is_validated_when_utc_instant_is_unknown(clock):
    value = example("current.request")
    value["records"][0]["observation"].update(source_time=clock, source_reported_at=None)
    with pytest.raises(TsetmcError):
        validate(value, "Batch")


@pytest.mark.parametrize("local_id", [str(2**63), "9999999999999999999", "1\n"])
def test_review_evidence_ids_use_the_same_complete_int64_domain(local_id):
    value = example("confirmation.request")
    value["records"][0]["observation"]["review"]["evidence_observation_ids"] = ["2", local_id]
    with pytest.raises(TsetmcError):
        validate(value, "Batch")


@pytest.mark.parametrize("text", ["\ud800", "\udfff", "valid\ud800invalid"])
def test_unpaired_surrogates_are_rejected_before_utf8_hashing(text):
    value = example("current.request")
    observation = value["records"][0]["observation"]
    observation["instrument_state_title"] = text
    observation["financial_hash"] = financial_hash(observation)
    value = decode(json.dumps(value, ensure_ascii=True).encode())
    with pytest.raises(TsetmcError, match="invalid_batch"):
        validate(value, "Batch")


def test_persian_metadata_and_int64_evidence_bound_remain_valid():
    value = example("current.request")
    observation = value["records"][0]["observation"]
    observation["instrument_state_title"] = "نماد آزمایشی"
    observation["financial_hash"] = financial_hash(observation)
    validate(decode(canonical(value)), "Batch")
    value = example("confirmation.request")
    value["records"][0]["observation"]["review"]["evidence_observation_ids"] = [
        str(2**63 - 2),
        str(2**63 - 1),
    ]
    validate(value, "Batch")


@pytest.mark.parametrize("entry", MANIFEST["examples"], ids=lambda e: e["file"])
def test_all_published_examples(entry):
    Draft202012Validator.check_schema(schema())
    body = (DIRECTORY / entry["file"]).read_bytes()
    assert hashlib.sha256(body).hexdigest() == entry["sha256"]
    value = decode(body)
    validate(value, entry["definition"])
    if entry["definition"] == "Batch":
        receipt = decode((DIRECTORY / entry["file"].replace("request", "receipt")).read_bytes())
        assert receipt["payload_sha256"] == hashlib.sha256(body).hexdigest()
        for record, result in zip(value["records"], receipt["records"], strict=True):
            independent = {k: record[k] for k in ("kind", "event_type", "observation")}
            encoded = json.dumps(
                independent, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            ).encode()
            assert (
                hashlib.sha256(encoded).hexdigest()
                == record_hash(record)
                == result["record_sha256"]
            )
    if entry["definition"] == "ReconcileResponse":
        assert digest(value["rows"]) == value["page_sha256"]


def test_contract_payloads_survive_windows_checkout_filters():
    root = Path(__file__).resolve().parents[1]
    for entry in MANIFEST["examples"]:
        path = (DIRECTORY / entry["file"]).relative_to(root).as_posix()
        body = subprocess.check_output(
            ["git", "-c", "core.autocrlf=true", "cat-file", "--filters", "HEAD:" + path],
            cwd=root,
            timeout=10,
        )
        assert hashlib.sha256(body).hexdigest() == entry["sha256"]


@pytest.mark.parametrize(
    "case",
    [
        "number",
        "scale",
        "exponent",
        "negative",
        "unknown",
        "hash",
        "count",
        "position",
        "bool",
        "naive",
        "invalid_date",
        "finality",
        "revoked_confirmed",
        "confirm_unverified",
        "reverse",
        "duplicate",
        "identity",
        "units",
        "clock",
        "current_version",
        "repeat",
        "correction_reason",
    ],
)
def test_strict_negative_cases(case):
    value = example(
        "current.request"
        if case in {"clock", "current_version", "repeat", "correction_reason"}
        else "confirmation.request"
    )
    record = value["records"][0]
    observation = record["observation"]
    if case in {"number", "scale", "exponent", "negative"}:
        observation["measurements"]["official_close"] = {
            "number": 112,
            "scale": "112.0",
            "exponent": "1e2",
            "negative": "-1",
        }[case]
    elif case == "unknown":
        observation["extra"] = "synthetic"
    elif case == "hash":
        observation["financial_hash"] = "0" * 64
    elif case == "count":
        observation["measurements"]["trade_count"] = "7.1"
    elif case == "position":
        record["source_position"] = str(2**63)
    elif case == "bool":
        value["session_generation"] = True
    elif case == "naive":
        observation["source"]["received_at"] = "2026-03-21T10:00:00"
    elif case == "invalid_date":
        observation["trading_date"] = "2026-02-30"
    elif case == "finality":
        observation["upstream_finality"] = "source_finalized"
    elif case == "revoked_confirmed":
        record["event_type"] = "daily.review_revoked"
    elif case == "confirm_unverified":
        observation["local_finalization"] = "source_unverified"
    elif case == "reverse":
        value["records"].append(example("daily.request")["records"][0])
    elif case == "duplicate":
        value["records"].append(copy.deepcopy(record))
    elif case == "identity":
        observation["ins_code"] = "090000000000000001"
    elif case == "units":
        observation["units"]["price_currency"] = "TOMAN"
    elif case == "clock":
        observation["source_reported_at"] = "2026-03-21T01:00:00Z"
    elif case == "current_version":
        observation["state_version"] = "9"
    elif case == "repeat":
        observation["accepted_decision"] = "repeated_state"
    else:
        observation["accepted_decision"] = "explicit_same_time_correction"
    with pytest.raises(TsetmcError):
        validate(value, "Batch")


@pytest.mark.parametrize(
    "body", [b'{"a":1,"a":2}', b'{"x":1.0}', b'{"x":NaN}', b'{"x":Infinity}', b"[]", b"\xff"]
)
def test_ambiguous_json(body):
    with pytest.raises(TsetmcError):
        decode(body)


def test_direct_decoder_body_budget_and_in_memory_float_are_rejected():
    with pytest.raises(TsetmcError, match="body_limit_exceeded"):
        decode(b" " * (2 * 1024 * 1024 + 1))
    value = example("daily.request")
    value["protocol_version"] = 1.0
    with pytest.raises(TsetmcError):
        validate(value, "Batch")


def test_financial_unicode_and_precision_hash_algorithms():
    observation = example("current.request")["records"][0]["observation"]
    observation["instrument_state_title"] = "نمونه مصنوعی"
    observation["measurements"]["previous_close"] = "100.12345678901234567890123456789"
    state = {
        "ins_code": observation["ins_code"],
        **observation["measurements"],
        "instrument_state": observation["instrument_state"],
        "instrument_state_title": observation["instrument_state_title"],
    }
    state["trade_count"] = int(state["trade_count"])
    expected = hashlib.sha256(
        json.dumps(state, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert financial_hash(observation) == expected
    assert expected != hashlib.sha256(canonical(state)).hexdigest()
