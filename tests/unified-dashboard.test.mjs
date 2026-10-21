import assert from "node:assert/strict";
import {MarketDataClient} from "../examples/unified-dashboard.mjs";
const calls = [];
const client = new MarketDataClient("https://company.example", async url => {
  calls.push(new URL(url));
  return {ok: true, json: async () => ({items: []})};
});
const iran = {provider: "tsetmc", provider_symbol: "900000000000000001"};
await client.latest(iran);
assert.equal(calls.at(-1).pathname, "/api/v1/tsetmc/latest");
await client.history(iran, {start:"2026-01-01", end:"2027-01-01", interval:"1d"});
assert.equal(calls.at(-1).searchParams.get("selection"), "finalized");
assert.throws(() => client.history(iran, {interval:"1m"}), /native daily/);
await client.history({provider:"tradingview_guest", canonical_symbol:"CRYPTO:BTCUSDT"}, {start:"2026-01-01T00:00:00Z", end:"2026-01-02T00:00:00Z"});
assert.equal(calls.at(-1).pathname, "/api/v1/candles");
assert.equal(new URL(client.streamURL(iran, "cursor")).searchParams.get("after"), "cursor");
console.log("Unified dashboard routing passed");
