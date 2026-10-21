"""Create private, matching first-install files; never overwrite existing identities."""

import argparse
import hashlib
import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5


def prepare(args: argparse.Namespace) -> None:
    endpoint = urlsplit(args.endpoint)
    if (
        endpoint.scheme != "https"
        or not endpoint.hostname
        or endpoint.username
        or endpoint.password
        or endpoint.path not in {"", "/"}
        or endpoint.query
        or endpoint.fragment
    ):
        raise ValueError("HTTPS origin required")
    if (
        not args.ins_code.isascii()
        or not args.ins_code.isdigit()
        or not 1 <= len(args.ins_code) <= 20
    ):
        raise ValueError("invalid ins_code")
    output = args.output.resolve()
    if output.exists():
        raise ValueError(
            "output already exists; retain identities and repair configuration explicitly"
        )
    producer, epoch, session, installation, seed = (str(uuid4()) for _ in range(5))
    key_id = "tsetmc_" + uuid4().hex
    token = key_id + "." + secrets.token_urlsafe(32)
    instrument = str(uuid5(NAMESPACE_URL, "marketdata:instrument:TSETMC:" + args.ins_code))
    streams = [
        dict(
            instrument_id=instrument,
            provider="tsetmc",
            stream=s,
            source_epoch=epoch,
            ownership_generation=1,
        )
        for s in ("tsetmc_daily", "tsetmc_current", "tsetmc_coverage", "tsetmc_status")
    ]
    destination = str(UUID(args.destination_id))
    files = {
        "company-plan.json": dict(
            destination_id=destination,
            ins_code=args.ins_code,
            display_name=args.display_name,
            exchange=args.exchange,
            source_instrument_id=args.source_instrument_id,
            approval_evidence=args.approval_evidence,
            units=json.loads(args.units_file.read_text(encoding="utf8")),
            producer=dict(
                producer_id=producer,
                label="TSETMC collector",
                key_id=key_id,
                session_id=session,
                streams=streams,
                allowed_statuses=["unknown"],
            ),
        ),
        "source-binding.json": dict(
            ins_code=args.ins_code,
            source_epoch=epoch,
            installation_id=installation,
            producer_id=producer,
            destination_id=destination,
            seed_id=seed,
        ),
        "worker.json": dict(
            endpoint=args.endpoint,
            ins_code=args.ins_code,
            producer_id=producer,
            destination_id=destination,
            session_id=session,
            session_generation=1,
            token_file=str(output / "producer.token"),
            anchor_file=str(output / "continuity.json"),
        ),
        "producer-credential.json": [
            dict(
                producer_id=producer,
                key_id=key_id,
                token_sha256=hashlib.sha256(token.encode()).hexdigest(),
            )
        ],
    }
    output.mkdir(parents=True, mode=0o700)
    for name, value in files.items():
        path = output / name
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
        os.chmod(path, 0o600)
    (output / "producer.token").write_text(token, encoding="utf8")
    os.chmod(output / "producer.token", 0o600)
    print("Created private connection files; no database, provider or service was changed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("destination-id", "ins-code", "display-name", "exchange", "endpoint"):
        parser.add_argument("--" + flag, required=True)
    parser.add_argument("--source-instrument-id")
    parser.add_argument("--approval-evidence", required=True)
    parser.add_argument("--units-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    prepare(parser.parse_args())


if __name__ == "__main__":
    main()
