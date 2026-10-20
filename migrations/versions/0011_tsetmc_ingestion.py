"""Provider-isolated TSETMC destination; legacy history and source tracks are unchanged."""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

# Frozen prior function body, copied from 0009. CREATE OR REPLACE preserves ACLs.
RECOVERY_LEGACY = """CREATE OR REPLACE FUNCTION ingest_recover_session(p_producer
UUID,p_key
TEXT,p_request JSONB)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public AS $$
DECLARE
producer public.ingest_producers%ROWTYPE;
prior public.ingest_session_recoveries%ROWTYPE;
recovery UUID; previous_session UUID; previous_generation BIGINT;
manifest JSONB; normalized JSONB; digest BYTEA;
new_session UUID; recovered_at TIMESTAMPTZ; lease TIMESTAMPTZ;
result JSONB;
BEGIN
-- Validate even direct SQL calls; runtime has no table DML or
-- policy UPDATE.
IF p_request IS NULL OR jsonb_typeof(p_request)<>'object' OR
octet_length(p_request::text)>262144 OR
NOT p_request ?&
ARRAY['protocol_version','recovery_id','previous_session_id',
'previous_session_generation','streams'] OR
(SELECT count(*) FROM jsonb_object_keys(p_request))<>5 OR
p_request->'protocol_version'<>'1'::jsonb OR
jsonb_typeof(p_request->'previous_session_generation')<>'number' OR
NOT (p_request->>'previous_session_generation' ~
'^[1-9][0-9]{0,18}$') OR
jsonb_typeof(p_request->'streams')<>'array' THEN
RETURN jsonb_build_object('error','invalid_recovery');
END IF;
IF jsonb_array_length(p_request->'streams') NOT BETWEEN 1 AND 1000
THEN
RETURN jsonb_build_object('error','invalid_recovery');
END IF;
BEGIN
recovery := (p_request->>'recovery_id')::uuid;
previous_session := (p_request->>'previous_session_id')::uuid;
previous_generation :=
(p_request->>'previous_session_generation')::bigint;
IF recovery IS NULL OR previous_session IS NULL THEN
RETURN jsonb_build_object('error','invalid_recovery');
END IF;
IF EXISTS(SELECT 1 FROM jsonb_array_elements(p_request->'streams') s
WHERE
jsonb_typeof(s)<>'object' OR
NOT s ?& ARRAY['instrument_id','provider','stream','source_epoch',
'ownership_generation'] OR
(SELECT count(*) FROM jsonb_object_keys(s))<>5 OR
jsonb_typeof(s->'ownership_generation')<>'number' OR
NOT (s->>'ownership_generation' ~ '^[1-9][0-9]{0,18}$')) THEN
RETURN jsonb_build_object('error','invalid_recovery');
END IF;
IF EXISTS(SELECT 1 FROM jsonb_to_recordset(p_request->'streams') AS
s(
instrument_id UUID,provider TEXT,stream TEXT,source_epoch UUID,
ownership_generation BIGINT) WHERE instrument_id IS NULL OR
provider IS NULL OR provider !~ '^[a-z][a-z0-9_]{0,99}$' OR
stream IS NULL OR stream NOT IN
('candles','quotes','coverage','status')
OR
source_epoch IS NULL OR ownership_generation IS NULL OR
ownership_generation<1) THEN
RETURN jsonb_build_object('error','invalid_recovery');
END IF;
SELECT jsonb_agg(jsonb_build_object('instrument_id',s.instrument_id,
'provider',s.provider,'stream',s.stream,'source_epoch',s.source_epoch,
'ownership_generation',s.ownership_generation)
ORDER BY s.instrument_id,s.provider,s.stream) INTO manifest
FROM jsonb_to_recordset(p_request->'streams') AS s(instrument_id
UUID,
provider TEXT,stream TEXT,source_epoch UUID,ownership_generation
BIGINT);
EXCEPTION WHEN invalid_text_representation OR
numeric_value_out_of_range THEN
RETURN jsonb_build_object('error','invalid_recovery');
END;
IF (SELECT count(DISTINCT
(s->>'instrument_id',s->>'provider',s->>'stream'))
FROM jsonb_array_elements(manifest) s)<>jsonb_array_length(manifest)
THEN
RETURN jsonb_build_object('error','invalid_recovery');
END IF;
normalized :=
jsonb_build_object('protocol_version',1,'recovery_id',recovery,
'previous_session_id',previous_session,
'previous_session_generation',previous_generation,'streams',manifest);
digest := sha256(convert_to(normalized::text,'UTF8'));
SELECT * INTO producer FROM public.ingest_producers
WHERE producer_id=p_producer FOR UPDATE;
IF NOT FOUND OR NOT producer.enabled OR
producer.credential_key_id<>p_key
OR p_key IS NULL THEN
RETURN jsonb_build_object('error','producer_not_authorized');
END IF;
SELECT * INTO prior FROM public.ingest_session_recoveries
WHERE producer_id=p_producer AND recovery_id=recovery;
IF FOUND AND prior.request_sha256<>digest THEN
RETURN jsonb_build_object('error','recovery_payload_conflict');
END IF;
-- Producer first, then sorted stream rows: same order as
-- existing uploads.
-- Include rows now owned by someone else, so a racing transfer
-- is observed.
PERFORM 1 FROM public.ingest_source_owners o JOIN
jsonb_to_recordset(manifest)
AS s(instrument_id UUID,provider TEXT,stream TEXT,source_epoch UUID,
ownership_generation BIGINT)
ON
(o.instrument_id,o.provider,o.stream)=(s.instrument_id,s.provider,s.stream)
ORDER BY o.instrument_id,o.provider,o.stream FOR SHARE OF o;
IF (SELECT count(*) FROM public.ingest_source_owners WHERE
producer_id=p_producer)
<>jsonb_array_length(manifest) OR
EXISTS(SELECT 1 FROM jsonb_to_recordset(manifest) AS s(instrument_id
UUID,
provider TEXT,stream TEXT,source_epoch UUID,ownership_generation
BIGINT)
LEFT JOIN public.ingest_source_owners o ON

(o.instrument_id,o.provider,o.stream)=(s.instrument_id,s.provider,s.stream)
WHERE (o.producer_id,o.source_epoch,o.ownership_generation) IS
DISTINCT
FROM
(p_producer,s.source_epoch,s.ownership_generation)) THEN
RETURN jsonb_build_object('error','recovery_ownership_changed');
END IF;
IF prior.recovery_id IS NOT NULL THEN
IF (producer.session_id,producer.session_generation) IS DISTINCT
FROM
(prior.session_id,prior.session_generation) THEN
RETURN jsonb_build_object('error','recovery_obsolete');
END IF;
-- Safe lost-response replay, even if that lease has since
-- expired.
-- Never extend it or reveal any subsequent replacement session.
RETURN prior.receipt;
END IF;
IF (producer.session_id,producer.session_generation) IS DISTINCT
FROM
(previous_session,previous_generation) THEN
RETURN jsonb_build_object('error','producer_session_fenced');
END IF;
IF producer.session_expires_at>clock_timestamp() THEN
RETURN jsonb_build_object('error','producer_session_active');
END IF;
IF previous_generation=9223372036854775807 THEN
RETURN jsonb_build_object('error','session_generation_exhausted');
END IF;
new_session := gen_random_uuid();
recovered_at := clock_timestamp(); lease := recovered_at+interval
'120 seconds';
UPDATE public.ingest_producers SET session_id=new_session,
session_generation=previous_generation+1,session_expires_at=lease
WHERE producer_id=p_producer;
result :=
jsonb_build_object('protocol_version',1,'producer_id',p_producer,
'recovery_id',recovery,'previous_session_id',previous_session,
'previous_session_generation',previous_generation,'session_id',new_session,
'session_generation',previous_generation+1,'expires_at',lease,
'server_recovered_at',recovered_at,'state','committed','streams',manifest);
INSERT INTO public.ingest_session_recoveries VALUES
(p_producer,recovery,p_key,digest,

normalized,previous_session,previous_generation,new_session,previous_generation+1,
result,recovered_at);
RETURN result;
END $$;"""

OBJECTS = """CREATE SCHEMA company_tsetmc;
REVOKE ALL ON SCHEMA company_tsetmc FROM PUBLIC;
ALTER TABLE public.provider_instruments ADD CONSTRAINT
provider_instruments_tsetmc_binding
UNIQUE(instrument_id,provider,provider_symbol);
CREATE TABLE company_tsetmc.instrument_links (
provider TEXT NOT NULL DEFAULT 'tsetmc' CHECK(provider='tsetmc'),
ins_code TEXT NOT NULL
CHECK(ins_code ~ '^[1-9][0-9]{0,19}$'),
instrument_id UUID NOT NULL, source_instrument_id TEXT, units JSONB
NOT NULL,
approval_evidence TEXT NOT NULL CHECK(length(approval_evidence)
BETWEEN 1 AND 256),
enabled BOOLEAN NOT NULL DEFAULT FALSE, PRIMARY
KEY(provider,ins_code),
UNIQUE(instrument_id,provider),
FOREIGN KEY(instrument_id,provider,ins_code) REFERENCES
public.provider_instruments(instrument_id,provider,provider_symbol)
);
CREATE TABLE company_tsetmc.daily_records (instrument_id UUID NOT
NULL, provider TEXT NOT
NULL DEFAULT 'tsetmc' CHECK(provider='tsetmc'),
producer_id UUID NOT NULL, source_epoch UUID NOT NULL,
ownership_generation BIGINT NOT NULL
CHECK(ownership_generation>0),
source_position BIGINT NOT NULL CHECK(source_position>0),
observation_id UUID NOT NULL,
payload JSONB NOT NULL, state_sha256 TEXT NOT NULL
CHECK(state_sha256 ~ '^[0-9a-f]{64}$'),
server_ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
FOREIGN KEY(instrument_id,provider) REFERENCES
company_tsetmc.instrument_links(instrument_id,provider),
FOREIGN KEY(producer_id,source_epoch,observation_id,instrument_id,provider,
source_position,ownership_generation) REFERENCES
public.ingest_observations(producer_id,source_epoch,observation_id,instrument_id,
provider,source_position,ownership_generation)
DEFERRABLE INITIALLY
DEFERRED, previous_close NUMERIC CHECK (previous_close IS NULL OR
(previous_close >= 0 AND
previous_close NOT IN
('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
opening_price NUMERIC CHECK (opening_price IS NULL OR (opening_price
>= 0 AND opening_price
NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
last_traded_price NUMERIC CHECK (last_traded_price IS NULL OR
(last_traded_price >= 0 AND
last_traded_price NOT IN
('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
high NUMERIC CHECK (high IS NULL OR (high >= 0 AND high NOT IN
('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
low NUMERIC CHECK (low IS NULL OR (low >= 0 AND low NOT IN
('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
official_close NUMERIC CHECK (official_close IS NULL OR
(official_close >= 0 AND
official_close NOT IN
('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
trade_count NUMERIC CHECK (trade_count IS NULL OR (trade_count >= 0
AND trade_count NOT IN
('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
traded_volume NUMERIC CHECK (traded_volume IS NULL OR (traded_volume
>= 0 AND traded_volume
NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
traded_value NUMERIC CHECK (traded_value IS NULL OR (traded_value >=
0 AND traded_value NOT
IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
financial_hash TEXT NOT NULL
CHECK(financial_hash ~ '^[0-9a-f]{64}$'), state_version BIGINT NOT
NULL
CHECK(state_version>0),
trading_date DATE NOT NULL, financial_revision BIGINT NOT NULL
CHECK(financial_revision>0),
acceptance TEXT NOT NULL CHECK(acceptance IN
('observed','reconciled')),
upstream_finality TEXT NOT NULL
CHECK(upstream_finality='unverified'),
local_finalization TEXT NOT NULL CHECK(local_finalization IN
('source_unverified','operator_finalized')),
publication_state TEXT NOT NULL CHECK(publication_state IN
('provisional','unverified_history')),
PRIMARY KEY(instrument_id,provider,trading_date), CHECK(trade_count
IS NULL OR
trade_count=trunc(trade_count)),
CHECK(high IS NULL OR low IS NULL OR high>=low),
CHECK(high IS NULL OR low IS NULL OR low<=0 OR trade_count=0 OR
traded_volume=0 OR
((opening_price IS NULL OR opening_price BETWEEN low AND high) AND
(last_traded_price IS NULL OR last_traded_price BETWEEN low AND
high))));
CREATE TABLE company_tsetmc.daily_states (instrument_id UUID NOT
NULL, provider TEXT NOT
NULL DEFAULT 'tsetmc' CHECK(provider='tsetmc'),
producer_id UUID NOT NULL, source_epoch UUID NOT NULL,
ownership_generation BIGINT NOT NULL
CHECK(ownership_generation>0),
source_position BIGINT NOT NULL CHECK(source_position>0),
observation_id UUID NOT NULL,
payload JSONB NOT NULL, state_sha256 TEXT NOT NULL
CHECK(state_sha256 ~ '^[0-9a-f]{64}$'),
server_ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
FOREIGN KEY(instrument_id,provider) REFERENCES
company_tsetmc.instrument_links(instrument_id,provider),
FOREIGN KEY(producer_id,source_epoch,observation_id,instrument_id,provider,
source_position,ownership_generation) REFERENCES
public.ingest_observations(producer_id,source_epoch,observation_id,instrument_id,
provider,source_position,ownership_generation)
DEFERRABLE INITIALLY
DEFERRED, financial_hash TEXT NOT NULL CHECK(financial_hash ~
'^[0-9a-f]{64}$'),
state_version BIGINT NOT NULL CHECK(state_version>0), trading_date
DATE NOT NULL,
financial_revision BIGINT NOT NULL CHECK(financial_revision>0),
became_canonical BOOLEAN NOT
NULL,
published_event_id BIGINT, PRIMARY
KEY(instrument_id,provider,source_epoch,trading_date,state_version),
UNIQUE(producer_id,source_epoch,observation_id));
CREATE INDEX tsetmc_states_position ON
company_tsetmc.daily_states(instrument_id,provider,source_epoch,source_position,trading_date);
CREATE INDEX tsetmc_states_day ON
company_tsetmc.daily_states(instrument_id,provider,source_epoch,trading_date,state_version
DESC);
CREATE TABLE company_tsetmc.daily_revisions (instrument_id UUID NOT
NULL, provider TEXT NOT
NULL DEFAULT 'tsetmc' CHECK(provider='tsetmc'),
producer_id UUID NOT NULL, source_epoch UUID NOT NULL,
ownership_generation BIGINT NOT NULL
CHECK(ownership_generation>0),
source_position BIGINT NOT NULL CHECK(source_position>0),
observation_id UUID NOT NULL,
payload JSONB NOT NULL, state_sha256 TEXT NOT NULL
CHECK(state_sha256 ~ '^[0-9a-f]{64}$'),
server_ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
FOREIGN KEY(instrument_id,provider) REFERENCES
company_tsetmc.instrument_links(instrument_id,provider),
FOREIGN KEY(producer_id,source_epoch,observation_id,instrument_id,provider,
source_position,ownership_generation) REFERENCES
public.ingest_observations(producer_id,source_epoch,observation_id,instrument_id,
provider,source_position,ownership_generation)
DEFERRABLE INITIALLY
DEFERRED, trading_date DATE NOT NULL,
financial_revision BIGINT NOT NULL CHECK(financial_revision>=2),
PRIMARY
KEY(instrument_id,provider,source_epoch,trading_date,financial_revision));
CREATE TABLE company_tsetmc.current_latest (instrument_id UUID NOT
NULL, provider TEXT NOT
NULL DEFAULT 'tsetmc' CHECK(provider='tsetmc'),
producer_id UUID NOT NULL, source_epoch UUID NOT NULL,
ownership_generation BIGINT NOT NULL
CHECK(ownership_generation>0),
source_position BIGINT NOT NULL CHECK(source_position>0),
observation_id UUID NOT NULL,
payload JSONB NOT NULL, state_sha256 TEXT NOT NULL
CHECK(state_sha256 ~ '^[0-9a-f]{64}$'),
server_ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
FOREIGN KEY(instrument_id,provider) REFERENCES
company_tsetmc.instrument_links(instrument_id,provider),
FOREIGN KEY(producer_id,source_epoch,observation_id,instrument_id,provider,
source_position,ownership_generation) REFERENCES
public.ingest_observations(producer_id,source_epoch,observation_id,instrument_id,
provider,source_position,ownership_generation)
DEFERRABLE INITIALLY
DEFERRED, previous_close NUMERIC CHECK (previous_close IS NULL OR
(previous_close >= 0 AND
previous_close NOT IN
('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
opening_price NUMERIC CHECK (opening_price IS NULL OR (opening_price
>= 0 AND opening_price
NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
last_traded_price NUMERIC CHECK (last_traded_price IS NULL OR
(last_traded_price >= 0 AND
last_traded_price NOT IN
('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
high NUMERIC CHECK (high IS NULL OR (high >= 0 AND high NOT IN
('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
low NUMERIC CHECK (low IS NULL OR (low >= 0 AND low NOT IN
('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
official_close NUMERIC CHECK (official_close IS NULL OR
(official_close >= 0 AND
official_close NOT IN
('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
trade_count NUMERIC CHECK (trade_count IS NULL OR (trade_count >= 0
AND trade_count NOT IN
('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
traded_volume NUMERIC CHECK (traded_volume IS NULL OR (traded_volume
>= 0 AND traded_volume
NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
traded_value NUMERIC CHECK (traded_value IS NULL OR (traded_value >=
0 AND traded_value NOT
IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
financial_hash TEXT NOT NULL
CHECK(financial_hash ~ '^[0-9a-f]{64}$'), state_version BIGINT NOT
NULL
CHECK(state_version>0),
source_date DATE, source_time TIME, source_reported_at TIMESTAMPTZ,
received_at TIMESTAMPTZ,
PRIMARY KEY(instrument_id,provider), CHECK(trade_count IS NULL OR
trade_count=trunc(trade_count)),
CHECK(high IS NULL OR low IS NULL OR high>=low),
CHECK(high IS NULL OR low IS NULL OR low<=0 OR trade_count=0 OR
traded_volume=0 OR
((opening_price IS NULL OR opening_price BETWEEN low AND high) AND
(last_traded_price IS NULL OR last_traded_price BETWEEN low AND
high))));
CREATE TABLE company_tsetmc.daily_coverage (instrument_id UUID NOT
NULL, provider TEXT NOT
NULL DEFAULT 'tsetmc' CHECK(provider='tsetmc'),
producer_id UUID NOT NULL, source_epoch UUID NOT NULL,
ownership_generation BIGINT NOT NULL
CHECK(ownership_generation>0),
source_position BIGINT NOT NULL CHECK(source_position>0),
observation_id UUID NOT NULL,
payload JSONB NOT NULL, state_sha256 TEXT NOT NULL
CHECK(state_sha256 ~ '^[0-9a-f]{64}$'),
server_ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
FOREIGN KEY(instrument_id,provider) REFERENCES
company_tsetmc.instrument_links(instrument_id,provider),
FOREIGN KEY(producer_id,source_epoch,observation_id,instrument_id,provider,
source_position,ownership_generation) REFERENCES
public.ingest_observations(producer_id,source_epoch,observation_id,instrument_id,
provider,source_position,ownership_generation)
DEFERRABLE INITIALLY
DEFERRED, trading_date DATE NOT NULL,
captured_at TIMESTAMPTZ NOT NULL, PRIMARY
KEY(instrument_id,provider,trading_date));
CREATE TABLE company_tsetmc.source_status (instrument_id UUID NOT
NULL, provider TEXT NOT
NULL DEFAULT 'tsetmc' CHECK(provider='tsetmc'),
producer_id UUID NOT NULL, source_epoch UUID NOT NULL,
ownership_generation BIGINT NOT NULL
CHECK(ownership_generation>0),
source_position BIGINT NOT NULL CHECK(source_position>0),
observation_id UUID NOT NULL,
payload JSONB NOT NULL, state_sha256 TEXT NOT NULL
CHECK(state_sha256 ~ '^[0-9a-f]{64}$'),
server_ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
FOREIGN KEY(instrument_id,provider) REFERENCES
company_tsetmc.instrument_links(instrument_id,provider),
FOREIGN KEY(producer_id,source_epoch,observation_id,instrument_id,provider,
source_position,ownership_generation) REFERENCES
public.ingest_observations(producer_id,source_epoch,observation_id,instrument_id,
provider,source_position,ownership_generation)
DEFERRABLE INITIALLY
DEFERRED, session_id UUID NOT NULL,
session_generation BIGINT NOT NULL CHECK(session_generation>0),
captured_at TIMESTAMPTZ NOT
NULL,
expires_at TIMESTAMPTZ NOT NULL CHECK(expires_at>captured_at AND
expires_at<=captured_at+interval '120 seconds'),
PRIMARY KEY(instrument_id,provider));
CREATE TABLE company_tsetmc.event_clock (
singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK(singleton), epoch
UUID NOT NULL DEFAULT
gen_random_uuid(),
head BIGINT NOT NULL DEFAULT 0 CHECK(head>=0), floor BIGINT NOT NULL
DEFAULT 0
CHECK(floor>=0 AND floor<=head));
INSERT INTO company_tsetmc.event_clock(singleton) VALUES(TRUE);
CREATE TABLE company_tsetmc.events (instrument_id UUID NOT NULL,
provider TEXT NOT NULL
DEFAULT 'tsetmc' CHECK(provider='tsetmc'),
producer_id UUID NOT NULL, source_epoch UUID NOT NULL,
ownership_generation BIGINT NOT NULL
CHECK(ownership_generation>0),
source_position BIGINT NOT NULL CHECK(source_position>0),
observation_id UUID NOT NULL,
payload JSONB NOT NULL, state_sha256 TEXT NOT NULL
CHECK(state_sha256 ~ '^[0-9a-f]{64}$'),
server_ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
FOREIGN KEY(instrument_id,provider) REFERENCES
company_tsetmc.instrument_links(instrument_id,provider),
FOREIGN KEY(producer_id,source_epoch,observation_id,instrument_id,provider,
source_position,ownership_generation) REFERENCES
public.ingest_observations(producer_id,source_epoch,observation_id,instrument_id,
provider,source_position,ownership_generation)
DEFERRABLE INITIALLY
DEFERRED, id BIGINT PRIMARY KEY,
trading_date DATE, kind TEXT NOT NULL CHECK(kind IN (
'daily.accepted','daily.corrected','daily.reconciled','daily.review_confirmed','daily.review_revoked',
'daily.quality_changed','daily.seed','daily.resnapshot','current.updated','current.position_updated',
'current.seed','current.resnapshot','coverage.updated','status.updated')),
measurements_changed BOOLEAN, recorded_at TIMESTAMPTZ NOT NULL
DEFAULT clock_timestamp());
CREATE INDEX tsetmc_events_instrument ON
company_tsetmc.events(instrument_id,id);
CREATE UNIQUE INDEX ingest_tsetmc_position ON
public.ingest_observations
(producer_id,instrument_id,provider,source_epoch,stream,source_position)
WHERE stream LIKE
'tsetmc_%';
CREATE FUNCTION company_tsetmc.immutable() RETURNS trigger LANGUAGE
plpgsql
SET search_path=pg_catalog,company_tsetmc AS $$ BEGIN
RAISE EXCEPTION 'immutable TSETMC history' USING ERRCODE='23514';
END $$;
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON
company_tsetmc.daily_states
FOR EACH ROW EXECUTE FUNCTION company_tsetmc.immutable();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON
company_tsetmc.daily_revisions
FOR EACH ROW EXECUTE FUNCTION company_tsetmc.immutable();
CREATE TRIGGER immutable BEFORE UPDATE ON company_tsetmc.events
FOR EACH ROW EXECUTE FUNCTION company_tsetmc.immutable();
REVOKE ALL ON FUNCTION company_tsetmc.immutable() FROM PUBLIC;
CREATE FUNCTION company_tsetmc.lock_instrument(UUID)
RETURNS SETOF company_tsetmc.instrument_links LANGUAGE sql SECURITY DEFINER
SET search_path=pg_catalog,company_tsetmc AS $$
SELECT * FROM company_tsetmc.instrument_links
WHERE instrument_id=$1 AND provider='tsetmc' FOR SHARE
$$;
REVOKE ALL ON FUNCTION company_tsetmc.lock_instrument(UUID) FROM PUBLIC;
CREATE FUNCTION company_tsetmc.prune_events(keep_count INTEGER)
RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER SET
search_path=pg_catalog,company_tsetmc AS $$
DECLARE tail BIGINT; boundary BIGINT; BEGIN
IF keep_count NOT BETWEEN 1 AND 1000000 THEN RAISE EXCEPTION
'invalid retention'; END IF;
SELECT head INTO tail FROM company_tsetmc.event_clock WHERE
singleton FOR UPDATE;
SELECT greatest(tail-keep_count,coalesce(max(id),0)) INTO boundary
FROM
company_tsetmc.events
WHERE recorded_at < clock_timestamp()-interval '7 days';
DELETE FROM company_tsetmc.events WHERE id<=boundary;
UPDATE company_tsetmc.event_clock SET floor=greatest(floor,boundary)
WHERE singleton;
END $$;
REVOKE ALL ON FUNCTION company_tsetmc.prune_events(INTEGER) FROM
PUBLIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
old_previous_close NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
old_opening_price NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
old_last_traded_price NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN old_high
NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN old_low
NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
old_official_close NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
old_trade_count NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
old_traded_volume NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
old_traded_value NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
new_previous_close NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
new_opening_price NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
new_last_traded_price NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN new_high
NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN new_low
NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
new_official_close NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
new_trade_count NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
new_traded_volume NUMERIC;
ALTER TABLE company_tsetmc.daily_revisions ADD COLUMN
new_traded_value NUMERIC;"""
LEGACY = "'candles','quotes','coverage','status'"
EXTENDED = LEGACY + ",'tsetmc_daily','tsetmc_current','tsetmc_coverage','tsetmc_status'"


def streams(values: str) -> None:
    for table in ("ingest_source_owners", "ingest_batches", "ingest_observations"):
        op.execute(f"""ALTER TABLE public.{table} DROP CONSTRAINT {table}_stream_check""")
        op.execute(
            f"""ALTER TABLE public.{table} ADD CONSTRAINT {table}_stream_check
CHECK(stream IN ({values}))"""
        )


def upgrade() -> None:
    # The old PK already makes this combination unique; old observations remain unchanged.
    op.execute("""ALTER TABLE public.ingest_observations ADD CONSTRAINT
        ingest_tsetmc_observation_context UNIQUE(producer_id,source_epoch,observation_id,
        instrument_id,provider,source_position,ownership_generation)""")
    op.execute(OBJECTS)
    for side in ("old", "new"):
        for field in (
            "previous_close",
            "opening_price",
            "last_traded_price",
            "high",
            "low",
            "official_close",
            "trade_count",
            "traded_volume",
            "traded_value",
        ):
            column = side + "_" + field
            op.execute(f"""ALTER TABLE company_tsetmc.daily_revisions ADD CHECK
                ({column} IS NULL OR ({column}>=0 AND {column} NOT IN
                ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric)))""")
        op.execute(f"""ALTER TABLE company_tsetmc.daily_revisions ADD CHECK
            ({side}_trade_count IS NULL OR {side}_trade_count=trunc({side}_trade_count))""")
    streams(EXTENDED)
    op.execute(RECOVERY_LEGACY.replace(LEGACY, EXTENDED))


def downgrade() -> None:
    # Never silently delete imported data, approved bindings or producer policy.
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM company_tsetmc.instrument_links)
OR EXISTS(SELECT 1 FROM public.ingest_source_owners WHERE stream
LIKE 'tsetmc_%')
OR EXISTS(SELECT 1 FROM public.ingest_batches WHERE stream LIKE
'tsetmc_%')
OR EXISTS(SELECT 1 FROM public.ingest_observations WHERE stream LIKE
'tsetmc_%')
THEN RAISE EXCEPTION
'TSETMC state exists; restore/cutover requires review'; END IF;
END $$""")
    op.execute(RECOVERY_LEGACY)
    streams(LEGACY)
    op.execute("""DROP INDEX public.ingest_tsetmc_position""")
    op.execute("""DROP SCHEMA company_tsetmc CASCADE""")
    op.execute("""ALTER TABLE public.ingest_observations
        DROP CONSTRAINT ingest_tsetmc_observation_context""")
    op.execute(
        """ALTER TABLE public.provider_instruments DROP CONSTRAINT
provider_instruments_tsetmc_binding"""
    )
