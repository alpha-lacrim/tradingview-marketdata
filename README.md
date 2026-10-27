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

Both collectors are temporarily limited to four instruments. TradingView collects
native 1m/5m/15m/1d bars (up to 4,999 per interval requested) and quote snapshots.
TSETMC collects daily history, current prices and trade-derived 1m candles with
5m/15m API aggregation. See [update steps and intraday limits](docs/native-intraday.md) and
[coverage and instrument list](docs/native-instruments.md). Neither
transport success nor a configured symbol proves complete or real-time coverage.

[Current state and checks](HANDOFF.md) | [Workspace/checkpoints](docs/workspace.md)

Existing databases, release packages and Docker files are preserved as legacy
recovery material and are not used by the native commands. Native storage starts
in a new database; old archives are not imported automatically. See the
[previous README](docs/history/readme-before-native-install.md) for the older platform.
