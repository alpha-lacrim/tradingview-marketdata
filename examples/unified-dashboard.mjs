/** One company origin, exact decimal strings, explicit market-specific semantics.
 * Call through your authenticated same-origin BFF; never embed a service token here.
 */
export class MarketDataClient {
  constructor(origin = "", fetcher = globalThis.fetch) {
    this.origin = origin;
    this.fetcher = fetcher;
  }
  async get(path, parameters = {}) {
    const query = new URLSearchParams(Object.entries(parameters).filter(([, v]) => v != null));
    const response = await this.fetcher(`${this.origin}${path}?${query}`, {credentials: "same-origin"});
    if (!response.ok) throw new Error(`Market data request failed: ${response.status}`);
    return response.json();
  }
  sources(after = "") {
    return this.get("/api/v1/instruments", {after, limit: 100});
  }
  iranianSources(after = "0") {
    return this.get("/api/v1/tsetmc/instruments", {after, limit: 100});
  }
  latest(source) {
    return source.provider === "tsetmc"
      ? this.get("/api/v1/tsetmc/latest", {ins_code: source.provider_symbol})
      : this.get("/api/v1/prices/latest", {provider: source.provider, symbols: source.canonical_symbol});
  }
  history(source, {start, end, interval = "1m", cursor, selection = "finalized"}) {
    if (source.provider === "tsetmc") {
      if (interval !== "1d") throw new Error("TSETMC history is native daily data");
      return this.get("/api/v1/tsetmc/daily", {ins_code: source.provider_symbol, start, end, after: cursor, selection, limit: 1000});
    }
    return this.get("/api/v1/candles", {symbol: source.canonical_symbol, provider: source.provider, start, end, interval, cursor, limit: 1000});
  }
  streamURL(source, after) {
    const url = new URL(this.origin || globalThis.location.origin);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = source.provider === "tsetmc" ? "/api/v1/ws/tsetmc" : "/api/v1/ws/marketdata";
    if (source.provider === "tsetmc") {
      url.searchParams.set("ins_code", source.provider_symbol);
      if (after) url.searchParams.set("after", after);
    }
    return url.toString();
  }
}
