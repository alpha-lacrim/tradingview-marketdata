-- Native profile v1. Separate from legacy Alembic databases and migrations.
CREATE SCHEMA IF NOT EXISTS simple_marketdata;
CREATE TABLE IF NOT EXISTS simple_marketdata.version (
    version integer PRIMARY KEY CHECK (version = 1)
);
INSERT INTO simple_marketdata.version VALUES (1) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS simple_marketdata.records (
    market text NOT NULL, symbol text NOT NULL, interval text NOT NULL,
    time bigint NOT NULL, received_at timestamptz NOT NULL,
    stored_at timestamptz NOT NULL DEFAULT clock_timestamp(), data jsonb NOT NULL,
    PRIMARY KEY (market, symbol, interval, time)
);
CREATE TABLE IF NOT EXISTS simple_marketdata.changes (
    id bigserial PRIMARY KEY,
    market text NOT NULL, symbol text NOT NULL, interval text NOT NULL, time bigint NOT NULL,
    received_at timestamptz NOT NULL, stored_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    previous jsonb, data jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS changes_source_cursor
ON simple_marketdata.changes(market, symbol, id);
CREATE TABLE IF NOT EXISTS simple_marketdata.receipts (
    batch_id uuid PRIMARY KEY, sha256 text NOT NULL, accepted integer NOT NULL,
    stored_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS simple_marketdata.intraday_snapshots (
    market text NOT NULL, symbol text NOT NULL, interval text NOT NULL,
    trading_date date NOT NULL, received_at timestamptz NOT NULL,
    PRIMARY KEY (market, symbol, interval, trading_date)
);
CREATE OR REPLACE FUNCTION simple_marketdata.record_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO simple_marketdata.changes(market,symbol,interval,time,received_at,data)
        VALUES(NEW.market,NEW.symbol,NEW.interval,NEW.time,NEW.received_at,NEW.data);
    ELSIF NEW.data IS DISTINCT FROM OLD.data THEN
        INSERT INTO simple_marketdata.changes(market,symbol,interval,time,received_at,previous,data)
        VALUES(NEW.market,NEW.symbol,NEW.interval,NEW.time,NEW.received_at,OLD.data,NEW.data);
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS record_change ON simple_marketdata.records;
CREATE TRIGGER record_change AFTER INSERT OR UPDATE ON simple_marketdata.records
FOR EACH ROW EXECUTE FUNCTION simple_marketdata.record_change();
