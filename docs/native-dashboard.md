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
| a | Time | UTC interval start in Unix seconds |
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

TradingView supports `1m`, `5m`, `15m`, `1h`, `1d`; larger intervals aggregate only
stored native minutes. Missing minutes are never filled. A sparse/partial bucket
does not prove complete coverage. TSETMC supports native `1d` only; dates are
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
