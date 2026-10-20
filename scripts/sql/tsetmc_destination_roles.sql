-- Explicit additive grants AFTER 0011, for reviewed existing company principals.
-- Creates no role/login/credential, policy, registry binding or source epoch.
DO $$ BEGIN
    IF (SELECT version_num FROM public.alembic_version)<>'0011' OR
        (SELECT count(*) FROM pg_roles WHERE rolname IN
            ('marketdata_v11_read','marketdata_v11_ingest'))<>2 OR
        EXISTS(SELECT 1 FROM pg_roles WHERE rolname IN
            ('marketdata_v11_read','marketdata_v11_ingest') AND
            (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)) OR
        EXISTS(SELECT 1 FROM pg_class c JOIN pg_roles r ON r.oid=c.relowner
            WHERE r.rolname IN ('marketdata_v11_read','marketdata_v11_ingest')
            AND c.relnamespace IN ('public'::regnamespace,'company_tsetmc'::regnamespace))
    THEN RAISE EXCEPTION 'reviewed restricted company principals and head 0011 required'; END IF;
END $$;
GRANT USAGE ON SCHEMA company_tsetmc TO marketdata_v11_read,marketdata_v11_ingest;
GRANT SELECT ON company_tsetmc.instrument_links,company_tsetmc.daily_records,
    company_tsetmc.daily_states,company_tsetmc.daily_revisions,company_tsetmc.current_latest,
    company_tsetmc.daily_coverage,company_tsetmc.source_status,company_tsetmc.event_clock,
    company_tsetmc.events TO marketdata_v11_read;
GRANT SELECT ON company_tsetmc.instrument_links TO marketdata_v11_ingest;
GRANT SELECT,INSERT ON company_tsetmc.daily_states,company_tsetmc.daily_revisions,
    company_tsetmc.events TO marketdata_v11_ingest;
GRANT SELECT,INSERT,UPDATE ON company_tsetmc.daily_records,company_tsetmc.current_latest,
    company_tsetmc.daily_coverage,company_tsetmc.source_status TO marketdata_v11_ingest;
GRANT SELECT,UPDATE ON company_tsetmc.event_clock TO marketdata_v11_ingest;
GRANT EXECUTE ON FUNCTION company_tsetmc.prune_events(INTEGER) TO marketdata_v11_ingest;
GRANT EXECUTE ON FUNCTION company_tsetmc.lock_instrument(UUID) TO marketdata_v11_ingest;
ALTER ROLE marketdata_v11_read SET default_transaction_read_only=on;
