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

This selects the existing provisional 99-source business registry. The same native
provider identity/access/status checks still apply: configuring 99 sources does
not establish that all 99 are available. Failures are reported per source.
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
handshakes after a 60-second pause; provider access rejections remain fatal.
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

No PostgreSQL or company DB credentials are needed here. This collects the verified
Foolad identity (`46348559193224090`), current observations every 15 seconds and
available native daily history hourly. `--poll-seconds` and `--history-seconds`
adjust the periods. `--once` fetches history and current data once. Metadata and
source parsers are shared with the existing collector. Conflicting/malformed
history is rejected and reported, rather than partially presented as complete.

Default state directory: `.local/simple-tsetmc/`. Preserve it across restarts.
Broader Iranian instrument coverage and minute history are not claimed. Daily
records retain unverified finality; quote freshness includes the original source
time when supplied. Recent collection does not turn an old price into a live trade.

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
