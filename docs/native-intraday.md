# Four-instrument rollout and TSETMC intraday

The native collectors are temporarily capped at four instruments, including when
an older, larger registry or `--all-shares` is supplied. Existing stored instruments
are retained and may still appear in `/api/instruments`; the cap limits new
collection, not reads. Previously staged uploads drain unchanged before new work.

TradingView defaults to `config/instruments.tradingview-four.json`:
`BINANCE:BTCUSDT`, `OANDA:EURUSD`, `OANDA:XAUUSD`, `OANDA:WTICOUSD`.
The large registries remain available for a future expansion. Explicit registries
use their first four subscriptions. Native 1m/5m/15m/1d and quotes remain enabled.

TSETMC defaults to the first four shares in its packaged list:

| Symbol | insCode |
| --- | --- |
| فولاد | 46348559193224090 |
| ومعادن | 58931793851445922 |
| وبملت | 778253364357513 |
| تاصیکو | 23293437377896568 |

## Update order

Stop the collectors before updating. Update Server B first, using its existing
native database and existing `DATABASE_URL`; do not create/reset the database.

```bash
uv sync --frozen --no-dev --extra collector
uv run --no-sync marketdata-simple init
```

Then restart FastAPI, update/install both collectors and restart them with their
existing state directories. `init` adds the `simple_marketdata.intraday_snapshots`
table without dropping data. It remains explicit and refuses legacy databases.
The new API checks that this table exists at startup. An old API rejects the new
snapshot payload with HTTP 422; the collector preserves that upload on disk.

For the laptop, in three separate PowerShell windows:

```powershell
# Window 1: company API (keep your existing native DATABASE_URL setting)
cd C:\Users\Pouyan\PycharmProjects\tradingview-main-consolidation
uv sync --frozen --extra collector
uv run marketdata-simple init
uv run marketdata-simple serve --host 127.0.0.1 --port 8000
```

```powershell
# Window 2: TradingView
cd C:\Users\Pouyan\PycharmProjects\tradingview-main-consolidation
$env:COMPANY_API_URL = "http://127.0.0.1:8000"
uv run tradingview-simple --state-dir .local/laptop-test-tradingview
```

```powershell
# Window 3: TSETMC
cd C:\Users\Pouyan\PycharmProjects\tsetmc-marketdata
uv sync --frozen
$env:COMPANY_API_URL = "http://127.0.0.1:8000"
uv run tsetmc-simple --state-dir .local/laptop-test-tsetmc
```

Stop older copies with Ctrl+C first. Never remove pending JSON files to fix a
version mismatch. Updating code does not update already running processes.

## TSETMC collection and validation

The collector builds 1m OHLC/count/volume/value from actual individual trades.
It fetches the source's current session plus five recent completed trading dates
selected from daily history. Current sweeps pause 300 seconds after a sweep;
completed snapshots refresh hourly. `--intraday-days 0` disables this stream;
1..30 sets the completed-date window. `--intraday-seconds` controls the pause,
minimum 60 seconds. Daily history and latest prices remain independent streams.

The provider uses `Trade/GetTrade/{insCode}` for current trades and
`Trade/GetTradeHistory/{insCode}/{YYYYMMDD}/false` for dated history. Source dates
and source HHMMSS clocks are interpreted in Asia/Tehran, then converted to UTC.
Prices and sums use Decimal. Cancelled trades are excluded before exact duplicate
rows are collapsed; conflicting duplicates or invalid trades reject that snapshot.
No-trade minutes stay absent. No candles are manufactured from daily prices.

Completed snapshots must reconcile count, volume, value and trade OHLC against the
official daily summary. Their close is last trade, not official daily close. An
empty archive with positive daily activity fails validation, leaving stored bars
unchanged. A source gap is not a zero-volume trading day.

Current trade and summary requests can observe different moments in a moving
market. Valid current trades can therefore publish provisional candles with
`metadata.finality=provisional` and `history_validation.status=provisional`.
These uploads only upsert observed minutes; they cannot remove missing minutes.
When totals and prices reconcile, a snapshot can also remove minutes that no longer
have active trades. Current candles remain provisional even when totals match.

Each acknowledged day is atomic. Removed candles become internal tombstones with
`data.deleted=true`; REST charts/records omit them, while changes/WebSockets retain
the event. Consumers applying events directly must remove that candle. Previous
values remain in the database audit log. A per-day receive-time watermark prevents
old retries from resurrecting cancelled candles, including completely empty days.

The independent durable upload file is `intraday.json`. The short backfill replays
on restart; hourly refresh timers are in memory. Failure does not advance refresh
timers, and normal continuous collection retries. `--once` reports failed snapshots
after attempting the other instruments/dates. Source diagnostics remain in
`<state-dir>/diagnostics/validation.jsonl` with rotation. Payload usage remains in
`traffic.json`; full trade snapshots can cost several MB each.

## Dashboard checks

Open `/docs`, expand GET `/api/chart`, select `market=tsetmc`, enter the insCode,
and choose `interval=1m`, `5m`, `15m`, or `1d`.

```text
/api/chart?market=tsetmc&symbol=46348559193224090&interval=1m
/api/chart?market=tsetmc&symbol=46348559193224090&interval=5m
/api/chart?market=tsetmc&symbol=46348559193224090&interval=15m
/api/records?market=tsetmc&symbol=46348559193224090&interval=1m
```

Chart keys remain `a` time, `b` open, `c` close, `d` high, `e` low, `f` count,
`g` volume, `h` traded value, `i` null. Intraday close is the last executed price;
daily close remains the official daily close. Missing minutes are never filled.
5m/15m aggregate stored 1m rows, so use `source=auto` (default) or `aggregate`.
`source=native` is rejected for TSETMC 5m/15m. For 1m, the existing `X-Bar-Source:
native` header means stored minute rows; their metadata identifies derived trades.
`/api/records` exposes exact decimals and provisional/reconciliation metadata.

`/api/coverage` accepts `interval=1m` plus required `start`/`end` Unix seconds.
Its default remains daily for TSETMC. It reports absent slots, not guaranteed
missing trades: closures and quiet minutes also produce gaps.

## Limits

These are observed website APIs without a guaranteed archive SLA. An archive can
be absent even for a recent trading date. The default five-date window is a bounded
backfill, not all historical minute data. Older corrections outside that window are
not automatically refreshed. Provisional snapshots cannot safely remove missing
minutes until a reconciled snapshot is available. No real-time or complete-coverage
claim is made. Native daily history and latest observations continue separately.
