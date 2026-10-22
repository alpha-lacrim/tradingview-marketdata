# Company market data: FastAPI + TradingView collector

The default installation runs natively on Ubuntu, without Docker. Both collectors
send data over HTTP to one FastAPI service and one company PostgreSQL database.
Collectors need no database; small pending-upload files survive restarts.

**Start here: [Ubuntu installation](docs/native-install.md).**
Give the frontend team the [dashboard API guide](docs/native-dashboard.md).

After installing dependencies and setting DATABASE_URL on the API host:

```bash
uv run --no-sync marketdata-simple init
uv run --no-sync marketdata-simple serve
```

On the TradingView collector host, set COMPANY_API_URL and run:

```bash
uv run --no-sync tradingview-simple
```

Install the independent [TSETMC collector](https://github.com/alpha-lacrim/tsetmc-marketdata)
and point it at the same COMPANY_API_URL. Reads and uploads are open by default;
SIMPLE_UPLOAD_TOKEN is optional for uploads. Browser access supports CORS.

The dashboard receives its existing ChartData shape from `/api/chart`: a=time,
b=open, c=close, d=high, e=low, f=count, g=volume, h=value, i=null. Latest prices,
exact records, corrections and WebSockets use the same service. PostgreSQL retains
exact decimal strings in JSONB; only the legacy chart response converts to float64.

TradingView collects native 1-minute bars and latest quote snapshots. The default
100-source registry is provisional; actual availability must be checked. Recovery
is limited to the provider's available history (up to 1,440 minutes requested).
TSETMC discovers primary ordinary shares (745 candidates in the latest check),
with native daily history and paced current-price sweeps. See
[coverage and instrument list](docs/native-instruments.md). Neither
transport success nor a configured symbol proves complete or real-time coverage.

[Current state and checks](HANDOFF.md) | [Workspace/checkpoints](docs/workspace.md)

Existing databases, release packages and Docker files are preserved as legacy
recovery material and are not used by the native commands. Native storage starts
in a new database; old archives are not imported automatically. See the
[previous README](docs/history/readme-before-native-install.md) for the older platform.
