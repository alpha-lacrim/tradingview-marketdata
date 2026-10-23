# Simple Ubuntu installation

This is the default path for new installations. No Docker, TimescaleDB, collector
databases, separate ingestion service, producer registration or certificate files.

```text
TradingView collector --HTTP--\
                              FastAPI --> one company PostgreSQL --> dashboard
TSETMC collector -----HTTP--/
```

Each collector keeps two small pending-upload files. Keep its state directory on
disk across restarts. The company commits a whole batch before acknowledging it;
retrying the same bytes is safe. The API serves stored data while collectors are off.

## 1. Install the company API on Ubuntu

Run as the ordinary account that will own the services. PostgreSQL is needed only
on the company server. The commands use a local PostgreSQL socket and Ubuntu peer
authentication, so there is no database password to configure.

```bash
sudo apt update
sudo apt install -y postgresql postgresql-client git curl
sudo systemctl enable --now postgresql
sudo -u postgres createuser "$USER"
sudo -u postgres createdb --owner="$USER" company_marketdata

curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv python install 3.12
mkdir -p "$HOME/marketdata"
cd "$HOME/marketdata"
git clone https://github.com/alpha-lacrim/tradingview-marketdata.git
cd tradingview-marketdata
uv sync --frozen --no-dev --extra collector --python 3.12

export DATABASE_URL='postgresql:///company_marketdata?host=/var/run/postgresql'
uv run --no-sync marketdata-simple init
uv run --no-sync marketdata-simple serve
```

If the PostgreSQL role already exists, skip `createuser`. Create a **new** database
for this profile. `init` refuses legacy Alembic databases; it does not migrate the
old company or collector storage. It is safe to repeat against native schema v1.
Startup checks the schema but never initializes it implicitly.

For PostgreSQL on another host, use a regular URL instead:
`postgresql://USER:PASSWORD@HOST:5432/DATABASE`. Percent-encode special password
characters in that URL. This URL belongs only on the API server.

Open `http://SERVER:8000/docs` and `http://SERVER:8000/health`. Port 8000 must be
reachable from the collectors and dashboard. `--host` and `--port` can change the
listen address. Reads and uploads are open by default. Anyone who can reach this
API can upload data. Optionally set the same `SIMPLE_UPLOAD_TOKEN` on the API and
collectors; it protects uploads only. Browser reads remain open, with CORS enabled.

Installation references: [PostgreSQL on Ubuntu](https://www.postgresql.org/download/linux/ubuntu/),
[uv installation](https://docs.astral.sh/uv/getting-started/installation/),
[Python installation](https://docs.astral.sh/uv/guides/install-python/).

## 2. Start TradingView

On the collector machine, clone/install the same repository with the commands
above starting at the uv installation; **do not install PostgreSQL there**.
In its repository folder:

```bash
export COMPANY_API_URL='http://SERVER:8000'
uv run --no-sync tradingview-simple
```

This selects `config/instruments.tradingview-native100.json`: 50 Binance spot USDT
pairs ranked by captured TradingView 24-hour USD volume, 42 forex feeds (21 pairs
from each of OANDA and FXCM), five metals feeds and three OANDA energy feeds.
The frozen ranking does not rotate automatically. All 100 supplied native bars and
accepted quotes in a bounded live check; this is not a guarantee of continuing
availability or complete minute coverage. Failures are reported per source.
Select another existing registry with `--registry config/instruments.tradingview-pilot.json`.
The configured limit is 100 sources. Symbols in the API are exact provider symbols,
for example `BINANCE:BTCUSDT`, `OANDA:EURUSD` and `FX:EURUSD` remain distinct.

The collector fetches completed native 1-minute bars, revisits recent bars for
corrections, and refreshes its available history hourly. Initial/restart recovery
requests up to 1,440 minutes; `--history-minutes` can reduce that bound. Upstream
omissions and history beyond this horizon are not synthesized. Persisted company
history accumulates over time. Quotes use a separate stream and send latest
snapshots approximately every five seconds; this is not an archive of every tick.

`--once` sends one history cycle and exits, reporting provider failures as errors.
Normal operation retries connection closures and incomplete WebSocket HTTP
handshakes with 60-second backoff, increasing to five minutes on repeated
failures. Longer Retry-After values are honored; access rejections remain fatal.
The default pending-file directory is `.local/simple-tradingview/`; `--state-dir`
selects another durable directory. Only one collector may own a given directory.
If uploads fail, the pending batch stays on disk and new history acquisition waits.
An outage longer than the available provider history can leave an unrecoverable gap.

## 3. Start TSETMC

On its collector machine, install uv/Python as above, then:

```bash
cd "$HOME/marketdata"
git clone https://github.com/alpha-lacrim/tsetmc-marketdata.git
cd tsetmc-marketdata
uv sync --frozen --no-dev --python 3.12
export COMPANY_API_URL='http://SERVER:8000'
uv run --no-sync tsetmc-simple
```

No PostgreSQL or company DB credentials are needed here. The default loads a fixed
100-share TSETMC watchlist bundled with the source package. It does not depend on
market-watch discovery, which can return an empty list. Each instrument metadata
response is still verified before collecting current prices and native daily history.
Remove `--all-shares` from older commands to select the fixed list. That flag remains
an optional broader live-discovery mode.
Use repeated `--ins-code` arguments for a smaller watchlist, e.g.
`--ins-code 46348559193224090` retains Foolad-only operation.

The client shares paced requests across both streams. Latest sweeps take minutes
for 100 instruments (at least about 100 seconds), followed by `--poll-seconds` (15 seconds by default).
Full history refreshes per instrument every `--history-seconds` (86400 by default);
acknowledged history completion survives restarts. `--once` forces one full pass.
Malformed history skips that instrument visibly; unrelated instruments continue.
Access denials and permanent upload failures stop. The original pilot is untouched.

Default state directory: `.local/simple-tsetmc/`. Preserve pending files and the
history checkpoint across restarts. If intentionally replacing the company database,
archive that state directory and use a new one; the same URL cannot detect a DB reset.
No native minute history, full-market finality or 15-second freshness for every share
is claimed. Source timestamps remain unchanged. See [expanded coverage](native-instruments.md).

## 4. Connect the dashboard

Give the frontend team the API base URL and [native-dashboard.md](native-dashboard.md).
No frontend token or separate market backend is needed.

```text
GET /api/instruments
GET /api/chart?market=tradingview&symbol=BINANCE:BTCUSDT&interval=1m&start=1784246400&end=1784332800
GET /api/chart?market=tsetmc&symbol=46348559193224090&interval=1d
GET /api/latest?market=tsetmc&symbol=46348559193224090
WS  /api/ws?market=tradingview&symbol=BINANCE:BTCUSDT
```

The chart returns `a,b,c,d,e,f,g,h` arrays and `i:null`, directly matching the supplied
Go contract. Source decimals remain exact in storage; float64 conversion happens
only in this compatibility response. No frontend changes to that struct are needed.

If the existing dashboard uses HTTPS, its browser cannot call an HTTP API directly.
Route the API through the dashboard server's existing HTTPS proxy, or terminate TLS
there. For an existing Nginx HTTPS server, one location is enough:

```nginx
location /market-data/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 60s;
}
```

The browser base URL is then `https://DASHBOARD/market-data`; collectors can keep
using the direct HTTP URL. No second backend or separate read/ingest routing is needed.

## 5. Keep processes running

The supplied **user systemd units** assume the repositories were cloned under
`$HOME/marketdata` with the names above. On each host install only the units it needs.

API host:

```bash
printf '%s\n' 'DATABASE_URL=postgresql:///company_marketdata?host=/var/run/postgresql' > "$HOME/marketdata/api.env"
mkdir -p "$HOME/.config/systemd/user"
cp "$HOME/marketdata/tradingview-marketdata/deploy/native/marketdata-api.service" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now marketdata-api
sudo loginctl enable-linger "$USER"
```

Collector hosts:

```bash
printf '%s\n' 'COMPANY_API_URL=http://SERVER:8000' > "$HOME/marketdata/collector.env"
mkdir -p "$HOME/.config/systemd/user"
# Copy only the collector(s) installed on this host:
cp "$HOME/marketdata/tradingview-marketdata/deploy/native/tradingview-collector.service" "$HOME/.config/systemd/user/"
cp "$HOME/marketdata/tsetmc-marketdata/deploy/native/tsetmc-collector.service" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now tradingview-collector tsetmc-collector
sudo loginctl enable-linger "$USER"
```

If only one collector is installed, enable only its unit. Stop foreground copies
before starting services. These units keep retry files under
`$HOME/.local/share/marketdata/`. Inspect logs with
`journalctl --user -u marketdata-api -f` (or the collector unit name).

## Existing data and updating

Existing databases, frozen releases and Docker files remain legacy recovery material.
They are not used by these commands. New native storage starts empty and does not
automatically import historical rows from the old databases. Keep those archives,
especially TradingView data older than the provider's retrieval window.

Before updates, back up the company database with `pg_dump -Fc company_marketdata`
and retain pending upload files. Pull `main`, repeat `uv sync --frozen --no-dev`
(with `--extra collector` in the TradingView repository), then restart the units.
The native tables retain correction history and receipts; monitor database disk
usage. There is no automatic deletion of your historical data.

## Failure handling and troubleshooting

Uploads retain the exact pending batch until a matching receipt arrives. Transient
network errors, HTTP 408/429 and server 5xx responses retry after 30 seconds,
doubling up to five minutes. A longer numeric or HTTP-date Retry-After is honored.
Logs identify the failure type/status, pending filename, retry delay and recovery.
Do not delete pending files. Bad receipts and permanent upload rejections stop
rather than silently discarding data; check the API URL/token/schema and restart
with the same state directory after resolving the cause.

If the API stops responding on Windows, press Esc in its terminal to clear any
console text selection, then check /health and /openapi.json. Selection can block
console output; it is not the only possible cause of a hang. HTTP access logging
is off by default to reduce terminal output; enable `marketdata-simple serve
--access-log` when diagnosing requests. Startup and error logs remain enabled.
Database pool waits are bounded at five seconds and native database operations at
20 seconds. Handled database/network/timeouts return HTTP 503 with Retry-After: 30.
An unresponsive process/network can still time out without returning JSON.
WebSockets close with code 1013 on temporary database failures; reconnect with
the last processed cursor. These changes do not alter the chart response format.

TradingView logs distinguish completed requests, delivered bars and empty results.
A successful empty request is not proof of history coverage. Connection-close
codes and cause types are reported without raw response contents. Reduced history
concurrency survives reconnects; a fresh process starts at its configured limit.
Unexpected programming errors remain visible rather than being hidden by retries.

TSETMC retries temporary network/DNS/timeout/server failures during its initial
identity lookup. It drains already staged uploads first. Invalid identities and
access-denied responses still stop; it never bypasses source qualification.
