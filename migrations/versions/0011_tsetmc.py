"""Add Iranian equity projections without changing international financial storage."""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

STREAMS = "'candles','quotes','coverage','status'"
EXTENDED = STREAMS + ",'tsetmc_daily','tsetmc_current','tsetmc_coverage','tsetmc_status'"


def streams(values: str) -> None:
    for table in ("ingest_source_owners", "ingest_batches", "ingest_observations"):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {table}_stream_check")
        op.execute(f"ALTER TABLE {table} ADD CHECK (stream IN ({values}))")


def recovery(old: str, new: str) -> None:
    # Preserve the installed function's fencing and grants; change only its stream allowlist.
    op.execute(f"""DO $migration$ DECLARE definition TEXT; BEGIN
      SELECT pg_get_functiondef('ingest_recover_session(uuid,text,jsonb)'::regprocedure)
        INTO definition;
      IF position($old${old}$old$ in definition)=0 THEN
        RAISE EXCEPTION 'unexpected recovery function'; END IF;
      EXECUTE replace(definition,$old${old}$old$,$new${new}$new$);
    END $migration$""")


def upgrade() -> None:
    streams(EXTENDED)
    recovery(STREAMS, EXTENDED)
    op.execute("""
      CREATE SCHEMA company_tsetmc;
      REVOKE ALL ON SCHEMA company_tsetmc FROM PUBLIC;
      CREATE TABLE company_tsetmc.heads (
        instrument_id UUID NOT NULL REFERENCES instruments(id),
        stream TEXT NOT NULL CHECK(stream IN
          ('tsetmc_daily','tsetmc_current','tsetmc_coverage','tsetmc_status')),
        entity TEXT NOT NULL,
        producer_id UUID NOT NULL REFERENCES ingest_producers(producer_id),
        source_epoch UUID NOT NULL,
        ownership_generation BIGINT NOT NULL CHECK(ownership_generation>0),
        source_position BIGINT NOT NULL CHECK(source_position>0),
        observation_id UUID NOT NULL,
        payload JSONB NOT NULL,
        PRIMARY KEY(instrument_id,stream,entity)
      );
      -- Exact decimal strings in approved JSONB remain lossless; no float projection.
      CREATE TABLE company_tsetmc.clock (
        singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK(singleton),
        epoch UUID NOT NULL DEFAULT gen_random_uuid(),
        head BIGINT NOT NULL DEFAULT 0 CHECK(head>=0)
      );
      INSERT INTO company_tsetmc.clock(singleton) VALUES(TRUE);
      CREATE TABLE company_tsetmc.events (
        id BIGINT PRIMARY KEY,
        instrument_id UUID NOT NULL REFERENCES instruments(id),
        stream TEXT NOT NULL,
        event_type TEXT NOT NULL,
        payload JSONB NOT NULL,
        recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
      );
      CREATE INDEX tsetmc_events_instrument ON company_tsetmc.events(instrument_id,id);
      CREATE UNIQUE INDEX tsetmc_position ON ingest_observations
        (producer_id,source_epoch,instrument_id,stream,source_position)
        WHERE provider='tsetmc';
    """)


def downgrade() -> None:
    # Never silently delete imported financial evidence during rollback.
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT FROM ingest_observations WHERE provider='tsetmc')
      OR EXISTS(SELECT FROM ingest_source_owners WHERE provider='tsetmc') THEN
      RAISE EXCEPTION 'remove test TSETMC data explicitly before downgrade'; END IF; END $$""")
    op.execute("DROP INDEX tsetmc_position; DROP SCHEMA company_tsetmc CASCADE")
    recovery(EXTENDED, STREAMS)
    streams(STREAMS)
