# Dashboard interface

Use one API base URL for both markets. Reads require no token. Call
`GET /api/instruments` to discover sources that have actually reached PostgreSQL.
TradingView uses exact provider symbols; TSETMC uses insCode strings.
The directory accepts `market=tsetmc` or `market=tradingview`, `limit` (default 1000,
maximum 5000), and `offset`. Fetch subsequent pages until one is shorter than limit.
`display_name` is the latest quote metadata name when supplied, otherwise the source
ID. TSETMC names/company/ISIN metadata also appear on exact records and latest quotes.

## ChartData

`GET /api/chart?market=tradingview&symbol=BINANCE:BTCUSDT&interval=1m`

`GET /api/chart?market=tsetmc&symbol=46348559193224090&interval=1d`

Optional `start`/`end` are Unix **seconds**, inclusive start/exclusive end. The
default range is the last 30 days. Request at most 100,000 native bars at once;
larger ranges return HTTP 413 and should be split into shorter requests.

| JSON | Go field | Meaning |
|---|---|---|
| a | Time | Source bar start (native) or UTC bucket start (aggregate), Unix seconds |
| b | Open | Opening price |
| c | Close | TradingView native close; TSETMC official close |
| d | High | Native high |
| e | Low | Native low |
| f | Count | Trade count if known; otherwise compatibility zero |
| g | Volume | Source volume with retained unit metadata; otherwise compatibility zero |
| h | Value | Traded monetary value if supplied; otherwise compatibility zero |
| i | — | Always null, matching the supplied sample |

Arrays are chronological and equal length. Empty history returns empty arrays.
Unavailable OHLC rows are omitted, counted in `X-Missing-OHLC`. Unknown activity
fields become zero **only** in this legacy response, counted in `X-Zero-Placeholders`.
The exact source record and missing fields remain available from `/api/records`.
TradingView volume is never relabeled as monetary value just to resemble a sample.

TradingView collects native `1m`, `5m`, `15m`, `1d`; `1h` aggregates stored minutes.
`source=auto` (default) uses native rows when present in the requested range, otherwise
falls back to minute aggregation. It never mixes both within one response.
Use `source=native` to require native rows (empty if unavailable), or
`source=aggregate` to explicitly request the old UTC minute aggregation.
`X-Bar-Source` identifies the selection and is exposed to browsers. Native daily
timestamps preserve provider session boundaries, which may differ from UTC midnight. Missing minutes are never filled. A sparse/partial bucket
does not prove complete coverage. TSETMC supports trade-derived `1m`, aggregated
`5m`/`15m`, and native `1d`. See [intraday semantics and update steps](native-intraday.md).
Intraday close is last trade; daily dates are
labeled at UTC midnight, not presented as exchange event instants. Official close
may differ from last trade and can lie outside the executed high/low range.

## Latest, exact records and corrections

`GET /api/latest?market=tsetmc&symbol=46348559193224090`

Returns decimal strings in `data.last`, `data.bid`, `data.ask`,
`data.official_close` where available, plus `data.event_at`, source status,
`received_at`, `stored_at`, `source_age_seconds` and `receive_age_seconds`.
An absent source event time has null source age. TSETMC is not labeled real-time.

`GET /api/records?market=tsetmc&symbol=46348559193224090&interval=1d&start=0&limit=1000`

Returns exact decimal strings, nulls, source metadata and `next_start` for pagination.
The store retains revisions; `/api/changes?market=...&symbol=...&after=CURSOR`
returns up to 500 changes. Keep requesting from the returned cursor until empty.
Intraday removal events have `data.deleted=true`; remove that candle or reload the
chart. Exact records omit deleted candles. Provisional status and reconciliation
details are available in minute-record metadata.

## WebSocket

`ws://SERVER:8000/api/ws?market=tradingview&symbol=BINANCE:BTCUSDT`

The first message is `{"type":"snapshot","latest":...,"cursor":...}`.
Following `changes` messages include `items` and a cursor, approximately once per
second. Save the last fully handled cursor and pass `&after=CURSOR` on reconnect
to replay changes. For a simple dashboard, treat nonempty changes as a signal to
reload `/api/latest` and the visible `/api/chart` range. This avoids applying an
older replayed observation over a newer snapshot. A new or restored database needs
a fresh snapshot and cursor; do not reuse cursors across database replacements.

```javascript
const base = "http://SERVER:8000";
const query = new URLSearchParams({market: "tsetmc", symbol: "46348559193224090"});
const chart = await fetch(`${base}/api/chart?${query}`).then(r => {
  if (!r.ok) throw new Error(`Chart request failed: ${r.status}`);
  return r.json();
});
// chart has exactly a..h and i:null; pass it to your existing chart component.
```

For an HTTPS dashboard use its existing HTTPS proxy URL, as described in
[native-install.md](native-install.md). CORS cannot override browser mixed-content rules.

## TSETMC validation and source-clock semantics

Daily close is official close, not last trade; it can legitimately fall outside
the executed high/low range. Unknown fields stay null in exact records, and
zero-activity days remain stored. Native uploads reject negative TSETMC prices,
conflicting daily close/official_close, invalid open/last ranges and empty records.
TSETMC event times more than five minutes ahead of received_at are rejected by
local integrity policy; older event times remain valid. Keep collector clocks
synchronized. Current metadata labels the source-reported Tehran dEven/hEven
clock and includes the source instrument state, without inferring market sessions
or real-time status. State and recent HTTP receipt alone do not prove a new trade.

## Coverage and quote ordering

`GET /api/coverage?market=tradingview&symbol=BINANCE:BTCUSDT&start=1792800000&end=1792886400`
reports stored native bar count and unobserved time ranges for the requested
[start,end) range. Boundaries identify native UTC slots (60 seconds or 86400
seconds); ranges are end-exclusive. No exchange calendar is inferred: absent
slots may be closures or missing data. `completeness` remains `unverified`.
The native TradingView collector's maximum recovery window is 4999 minutes;
a smaller configured window is possible. This endpoint reports coverage only,
not a backfill job. Older gaps/corrections need a separately qualified source.

Chart JSON stays unchanged. `X-Partial-Buckets` counts returned buckets with
fewer usable native OHLC rows than a full interval. This includes query edges,
ongoing candles and legitimate source omissions, not just collection failures.
`X-Coverage-Status: unverified` prevents interpreting returned candles as proof
of complete history. Both headers are exposed to browser clients through CORS.

A quote without a source event timestamp cannot replace an already dated quote.
It can be stored initially if no dated quote exists. Older source timestamps
also cannot replace newer ones. `/api/latest` remains the latest accepted stored
observation, not an on-demand provider request. Check its event and receipt ages.


`/api/records` also accepts native `5m` and `15m`. `/api/coverage` still
measures TradingView **1m** storage only; it is not higher-timeframe coverage.
Native daily completion is conservative: the last returned provider bar is excluded,
and accepted starts must be at least 24 hours old. Provider session finality is not
independently verified, particularly around closures and daylight-saving changes.
