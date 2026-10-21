"""Copy the reviewed, transport-only contract from the independent sibling checkout."""

from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root.parent / "tsetmc-marketdata"
target = root / "src/marketdata/tsetmc"
target.mkdir(exist_ok=True)
(target / "__init__.py").write_text(
    '"""Iranian equity wire protocol and company projection; no collector imports."""\n'
)
(target / "schema.json").write_bytes(
    (source / "docs/contracts/milestone3b/schema.json").read_bytes()
)
wire = (source / "src/tsetmc_marketdata/storage/publication_wire.py").read_text()
wire = wire.replace("from importlib.resources import files\n", "")
wire = wire.replace(
    "from tsetmc_marketdata.models.daily import validate_measurements",
    "from marketdata.tsetmc.measurements import validate_measurements",
)
wire = wire.replace(
    "from tsetmc_marketdata.storage.serialization import canonical_hash",
    "from marketdata.tsetmc.measurements import canonical_hash",
)
start, end = (
    wire.index("    resource = files("),
    wire.index("    return result", wire.index("def schema(")),
)
wire = (
    wire[:start]
    + "    result: dict[str, Any] = json.loads(\n"
    + '        Path(__file__).with_name("schema.json").read_text(encoding="utf8"))\n'
    + wire[end:]
)
(target / "wire.py").write_text(wire, encoding="utf8")
daily = (source / "src/tsetmc_marketdata/models/daily.py").read_text()
validation = daily[
    daily.index("def validate_measurements(") : daily.index("def price_change(")
].replace("RecordError", "ValueError")
serialization = (source / "src/tsetmc_marketdata/storage/serialization.py").read_text()
helpers = serialization[
    serialization.index("def decimal_text(") : serialization.index("def financial_state(")
]
(target / "measurements.py").write_text(
    '"""Canonical tsetmc.v1 financial validation and hashing."""\n'
    "import hashlib\nimport json\nfrom datetime import date, datetime, time\n"
    "from decimal import Decimal\nfrom typing import Any\nfrom uuid import UUID\n\n"
    + validation
    + helpers,
    encoding="utf8",
)
