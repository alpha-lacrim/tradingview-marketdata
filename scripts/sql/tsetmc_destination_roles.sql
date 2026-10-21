-- Apply AFTER existing v11_destination_roles.sql, as destination administrator.
GRANT USAGE ON SCHEMA company_tsetmc TO marketdata_v11_read,marketdata_v11_ingest;
GRANT SELECT ON ALL TABLES IN SCHEMA company_tsetmc TO marketdata_v11_read,marketdata_v11_ingest;
GRANT INSERT,UPDATE ON company_tsetmc.heads TO marketdata_v11_ingest;
GRANT INSERT ON company_tsetmc.events TO marketdata_v11_ingest;
GRANT UPDATE ON company_tsetmc.clock TO marketdata_v11_ingest;
