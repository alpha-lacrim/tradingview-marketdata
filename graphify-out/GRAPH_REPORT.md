# Graph Report - tradingview-main-consolidation  (2026-10-22)

## Corpus Check
- 580 files · ~1,176,376 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 52 file(s) not represented in the graph (top: (none) 18, .lock 8, .ini 6)

## Summary
- 6965 nodes · 13836 edges · 347 communities (222 shown, 125 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 553 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b089794c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- benchmark_live_pool.py
- json
- src/marketdata/api.py
- pathlib
- marketdata-fastapi/tests/test_api_v1.py
- asyncio
- tests/test_market_stream.py
- test_tsetmc_http.py
- marketdata-fastapi/src/marketdata/market_stream.py
- Store
- test_source_capture.py
- marketdata-fastapi/src/marketdata/api.py
- src/marketdata/replication_models.py
- marketdata-fastapi-v1.1.0rc1/src/marketdata/api.py
- marketdata-fastapi-v1.1.0rc1/src/marketdata/replication_models.py
- test_simple_native.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/replication_models.py
- test_tradingview.py
- SyncWorker
- SyncWorker
- test_sync_worker.py
- src/marketdata/reconciliation.py
- marketdata-fastapi-v1.1.0rc1/src/marketdata/reconciliation.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/reconciliation.py
- qualify_v11_pipeline.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/providers/databento.py
- Store
- test_candle_pipeline.py
- tests/test_api_v1.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/source_capture.py
- src/marketdata/source_capture.py
- TsetmcWriter
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/api.py
- MarketHub
- src/marketdata/ingest_api.py
- CODEX.md
- test_destination_ingestion.py
- MarketDataProvider
- MarketDataProvider
- MarketDataProvider
- MarketDataProvider
- test_candle_reliability.py
- marketdata-fastapi/src/marketdata/providers/candle_pool.py
- _create_app
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/providers/candle_pool.py
- Milestone 3B: independent durable HTTPS worker
- Milestone 3B: independent durable HTTPS worker
- test_candle_pool.py
- test_session_recovery.py
- test_ingest_http.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/domain.py
- marketdata-fastapi/src/marketdata/domain.py
- marketdata-fastapi-v1.1.0rc1/src/marketdata/domain.py
- src/marketdata/domain.py
- test_dual_ingestion.py
- TsetmcError
- test_native_candles.py
- test_dual_collector_to_exact_released_api_outage_recovery_replay
- README.md
- Store
- src/marketdata/providers/tradingview_candles.py
- src/marketdata/ingestion.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/candle_ingestion.py
- src/marketdata/candle_ingestion.py
- test_process_separation.py
- src/marketdata/providers/candle_pool.py
- marketdata-fastapi/src/marketdata/candle_ingestion.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/events.py
- marketdata-fastapi/src/marketdata/ingestion.py
- test_tsetmc_ingestion.py
- create_app
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/providers/oanda.py
- src/marketdata/providers/oanda.py
- record
- fastapi-v1.1-milestone5.md
- logging
- Pipeline
- make_pool
- test_ingestion.py
- test_providers.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/api_v1.py
- Store
- pytest
- probe_native_history.py
- marketdata-fastapi/src/marketdata/providers/candles.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/collector.py
- marketdata-fastapi-v1.1.0rc1/src/marketdata/candles.py
- uuid
- create_app
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/providers/candles.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/providers/synthetic_candles.py
- test_databento_sdk.py
- src/marketdata/providers/synthetic_candles.py
- marketdata-fastapi-v1.1.0rc1/src/marketdata/api_models.py
- src/marketdata/providers/candles.py
- marketdata-fastapi/src/marketdata/api_models.py
- src/marketdata/api_models.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/api_models.py
- Market Data REST and WebSocket API v1
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/ingestion.py
- SyncWorker
- test_health_api.py
- marketdata-fastapi-v1.1.0rc1/src/marketdata/api_v1.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/sample_data.py
- Current state - 2026-10-20, M3B-2 integration checkpoint
- marketdata-fastapi/src/marketdata/sample_data.py
- src/marketdata/sample_data.py
- test_release_foundation.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/providers/tradingview.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/sync_worker.py
- test_integration_compatibility.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/collector.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/ingest_auth.py
- pydantic
- smoke_tradingview_candles.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/providers/factory.py
- decimal
- observe_dual_ingestion.py
- qualify_api.py
- marketdata-fastapi-v1.1.0rc1/src/marketdata/events.py
- marketdata-fastapi/src/marketdata/sessions.py
- src/marketdata/providers/binance.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/api_v1.py
- src/marketdata/cli.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/providers/binance.py
- retrieve
- marketdata-fastapi-v1.1.0rc1/src/marketdata/ingest_auth.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/cli.py
- src/marketdata/candle_benchmark.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/candle_benchmark.py
- src/marketdata/ws_models.py
- marketdata-fastapi/src/marketdata/ws_models.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/ws_models.py
- src/marketdata/events.py
- marketdata-fastapi-v1.1.0rc1/src/marketdata/ws_models.py
- FastAPI v1.1 — Milestone 4 verification
- MarketHub
- TradingViewGuestProvider
- marketdata-fastapi/tests/browser-marketdata.test.mjs
- Replay
- marketdata-fastapi-v1.1.0rc1/src/marketdata/session_recovery.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/session_recovery.py
- make_provider
- CandleConnectionPool
- math
- src/marketdata/providers/tradingview.py
- Socket
- install_marketdata_proxy
- src/marketdata/session_recovery.py
- SyncState
- Standalone Market Data FastAPI
- SyncState
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/candles.py
- test_api_production.py
- marketdata-fastapi/src/marketdata/candles.py
- src/marketdata/candles.py
- install_marketdata_proxy
- decimal
- v11_qualification_process.py
- FastAPI Batch 2 — completion report
- marketdata-fastapi/tests/conftest.py
- urllib_parse
- TSETMC M3B-2 company INGEST and storage
- dataclasses
- test_recovery_fanout.py
- socket
- Batch 4 employer qualification report — 2026-10-14
- FastAPI v1.1 integration — Phase A audit and design
- strict_json
- dataclasses
- destination
- src/marketdata/fanout.py
- marketdata-fastapi/src/marketdata/fanout.py
- Settings
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/sessions.py
- marketdata-fastapi-v1.1.0rc1/src/marketdata/sessions.py
- Experimental TradingView guest market data
- Tick
- reconcile_candles.py
- marketdata-fastapi-v1.1.0rc1/src/marketdata/price_selection.py
- Live guest candles through PostgreSQL
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/price_selection.py
- src/marketdata/price_selection.py
- marketdata-fastapi/src/marketdata/price_selection.py
- startMarketData
- datetime
- startMarketData
- startMarketData
- Market Data REST and WebSocket API v1
- src/marketdata/sessions.py
- Configurable candle connection pool
- Native candle retrieval scalability
- startMarketData
- retrieve
- Production deployment and recovery
- Shared dashboard integration on audited company storage
- test_actual_pytest_fixture_dependency_order
- .__call__
- src/marketdata/api_v1.py
- smoke_production_tradingview.py
- test_watchdog_uses_owned_runner_to_reconnect_and_restore
- Registry
- Registry
- Registry
- Employer business universe — provisional qualification, 2026-10-13
- Milestone 3B: independent durable HTTPS worker
- collector
- FrameDecoder
- Registry
- AGENTS.md
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/remote_status.py
- marketdata-fastapi/src/marketdata/config.py
- .__call__
- test_v11_qualification.py
- create_app
- SyncHTTP
- FastAPI v1.1 — milestone 1 destination foundation
- Platform reference
- test_ordinary_scaling.py
- SyncHTTP
- test_candle_pool_benchmark.py
- prices_socket
- render_event
- src/marketdata/providers/definitions.py
- render_event
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/quote_fields.py
- SyncConfig
- chart_data
- marketdata-fastapi-v1.1.0rc1/src/marketdata/quote_fields.py
- render_event
- Milestone 3A: local source capture and milestone 3B contract
- cursor
- test_production_tradingview_smoke.py
- Milestone 3A: local source capture and milestone 3B contract
- cursor
- FastAPI Batch 1: independent processes
- Milestone 3A review: durable local capture
- Milestone 2.1 — secure same-producer session recovery
- Milestone 3A: local source capture and milestone 3B contract
- Ordinary TradingView collector: 100-source qualification
- WebSocket market data v1
- Operations, backup/restore, reconciliation and application rollback
- provider
- Company frontend handoff
- Native availability investigation — 2026-10-12
- WebSocket market data v1
- re
- parse_bar
- src/marketdata/quote_fields.py
- marketdata-collector-sync-v1.1.0rc1/src/marketdata/quote_snapshots.py
- Current state - native installation, 2026-10-22
- FastAPI v1.1 — Milestone 3B review
- Ordinary collector instrument activation
- Standalone Market Data FastAPI
- 16. Database model
- SyncConfig
- Multi-asset market data
- InjectedQuotes
- Repository layout and existing checkout migration
- Verified collector / FastAPI Batch 1 integration
- collector/README.md
- Authorized commercial TradingView preparation
- Current state — 2026-10-21
- 30. Testing
- v11_qualification_source.py
- chart_data
- test_pipeline_interleaving_two_requests_routes_exact_symbols
- Company ingestion protocol v1 (FastAPI v1.1, milestone 2)
- Collector and FastAPI integration handoff
- 0011_tsetmc_ingestion.py
- 13. Timestamp handling
- Implemented execution protocol
- FastAPI v1.1 — milestone 2.1 review
- TradingViewCandleProvider
- company/INSTALL-COMPANY.md
- Settings
- chart_data
- FastAPI v1.1 — milestone 2 review
- CODEX.md
- marketdata-collector-sync-v1.1.0rc1/VERIFY.md
- common/COLLECTOR-TRANSITION.md
- common/VERIFY.md
- marketdata-fastapi
- marketdata-fastapi
- marketdata-collector-sync
- marketdata-platform
- M3B-2 disposable CI ownership
- Simple Ubuntu installation
- Simultaneous TradingView collection — 2026-10-14
- Company ingestion runtime — milestones 2, 2.1 and 3B
- Completed-development consolidation into main
- check_refs

## God Nodes (most connected - your core abstractions)
1. `make_candle()` - 81 edges
2. `TsetmcError` - 52 edges
3. `record()` - 38 edges
4. `Store` - 33 edges
5. `Store` - 33 edges
6. `Store` - 33 edges
7. `cursor()` - 31 edges
8. `Replay` - 31 edges
9. `provider()` - 29 edges
10. `_create_app()` - 28 edges

## Surprising Connections (you probably didn't know these)
- `Coverage` --references--> `provider()`  [INFERRED]
  distributions/marketdata-collector-sync-v1.1.0rc1/docs/api.md → scripts/qualify_ordinary_recovery.py
- `Instruments` --references--> `provider()`  [INFERRED]
  distributions/marketdata-collector-sync-v1.1.0rc1/docs/api.md → scripts/qualify_ordinary_recovery.py
- `Latest completed candles` --references--> `provider()`  [INFERRED]
  distributions/marketdata-collector-sync-v1.1.0rc1/docs/api.md → scripts/qualify_ordinary_recovery.py
- `Coverage` --references--> `provider()`  [INFERRED]
  distributions/marketdata-fastapi-v1.1.0rc1/docs/api.md → scripts/qualify_ordinary_recovery.py
- `Instruments` --references--> `provider()`  [INFERRED]
  distributions/marketdata-fastapi-v1.1.0rc1/docs/api.md → scripts/qualify_ordinary_recovery.py

## Import Cycles
- None detected.

## Communities (347 total, 125 thin omitted)

### Community 0 - "benchmark_live_pool.py"
Cohesion: 0.04
Nodes (19): probe(), rss_bytes(), run(), summarize(), persistence(), quantiles(), run(), summaries() (+11 more)

### Community 1 - "json"
Cohesion: 0.03
Nodes (39): main(), test_complete_file_manifest(), test_source_track_and_worker_are_present(), digest(), package(), test_exported_source_hashes(), test_openapi_contract_equals_verified_snapshot(), main() (+31 more)

### Community 2 - "src/marketdata/api.py"
Cohesion: 0.06
Nodes (40): authorized(), Candle, CandlePage, Command, create_app(), _create_app(), authenticate(), candles() (+32 more)

### Community 3 - "pathlib"
Cohesion: 0.04
Nodes (37): main(), create(), main(), main(), command(), DeploymentSettings, main(), command() (+29 more)

### Community 4 - "marketdata-fastapi/tests/test_api_v1.py"
Cohesion: 0.05
Nodes (55): forbidden(), make_candle(), snapshot(), api_client(), assert_chart_types(), brokers(), candle(), persist() (+47 more)

### Community 5 - "asyncio"
Cohesion: 0.03
Nodes (32): run(), smoke(), smoke(), audit(), probe(), run(), distribution(), inspect_container() (+24 more)

### Community 6 - "tests/test_market_stream.py"
Cohesion: 0.07
Nodes (25): factory(), main(), bar(), receive(), server(), settings(), subscribe(), test_authentication_and_origin_fail_before_registration() (+17 more)

### Community 7 - "test_tsetmc_http.py"
Cohesion: 0.08
Nodes (12): sync(), worker_tls_server(), ingress_tsetmc(), test_actual_child_process_death_and_replay(), test_actual_tls_upload_and_untrusted_certificate_rejected(), test_authenticated_upload_receipt_lookup_and_safe_errors(), test_binding_changes_serialize_with_restricted_ingest(), test_invalid_scalar_http_requests_are_422_with_no_import_writes() (+4 more)

### Community 8 - "marketdata-fastapi/src/marketdata/market_stream.py"
Cohesion: 0.08
Nodes (5): create_stream_router(), changes(), MarketClient, MarketHub, render_event()

### Community 10 - "test_source_capture.py"
Cohesion: 0.09
Nodes (35): migrate(), test_fresh_database_installs_current_head_and_optional_timescale(), test_populated_0006_upgrade_preserves_market_events_and_seeds_noop_heads(), make_candle(), extend(), quote(), source(), test_bounded_storage_backpressure_cleanup_and_safe_cursors() (+27 more)

### Community 11 - "marketdata-fastapi/src/marketdata/api.py"
Cohesion: 0.05
Nodes (41): authorized(), Candle, CandlePage, Command, create_app(), _create_app(), authenticate(), candles() (+33 more)

### Community 12 - "src/marketdata/replication_models.py"
Cohesion: 0.07
Nodes (19): Batch, CandleObservation, CandleRecord, canonical_bytes(), CapturedHealth, CapturedSymbolHealth, CoverageObservation, CoverageRecord (+11 more)

### Community 13 - "marketdata-fastapi-v1.1.0rc1/src/marketdata/api.py"
Cohesion: 0.06
Nodes (40): authorized(), Candle, CandlePage, Command, create_app(), _create_app(), authenticate(), candles() (+32 more)

### Community 14 - "marketdata-fastapi-v1.1.0rc1/src/marketdata/replication_models.py"
Cohesion: 0.07
Nodes (19): Batch, CandleObservation, CandleRecord, canonical_bytes(), CapturedHealth, CapturedSymbolHealth, CoverageObservation, CoverageRecord (+11 more)

### Community 15 - "test_simple_native.py"
Cohesion: 0.07
Nodes (23): create_app(), latest(), latest_row(), websocket(), Observation, body(), observation(), test_api_database_failures_return_retryable_503() (+15 more)

### Community 16 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/replication_models.py"
Cohesion: 0.07
Nodes (19): Batch, CandleObservation, CandleRecord, canonical_bytes(), CapturedHealth, CapturedSymbolHealth, CoverageObservation, CoverageRecord (+11 more)

### Community 17 - "test_tradingview.py"
Cohesion: 0.16
Nodes (8): captured_messages(), test_captured_guest_quotes_persist_and_latest_is_realtime(), test_captured_quotes_all_seventeen_sources_verified(), test_decoder_fragmentation_multiple_frames_and_utf16(), test_stream_heartbeat_malformed_json_wrong_session_and_disconnect(), test_unknown_messages_and_parse_logs_are_bounded(), connection(), wrap()

### Community 18 - "SyncWorker"
Cohesion: 0.21
Nodes (15): completed_candle(), create_router(), candles(), coverage(), dashboard_candles(), health(), instruments(), latest_candles() (+7 more)

### Community 19 - "SyncWorker"
Cohesion: 0.09
Nodes (10): candle_record(), quote_record(), candles(), publish_quotes(), quotes(), transport_delay(), transport_detail(), run() (+2 more)

### Community 20 - "test_sync_worker.py"
Cohesion: 0.06
Nodes (34): Previous and new architecture, Operational health and freshness, Crash-test harness timing, destination_process(), snapshot(), test_candle_reconciliation_hash_preserves_arbitrary_decimal_precision(), test_commit_fence_rolls_back_inflight_local_transaction(), test_competing_worker_processes_cannot_claim_or_mutate() (+26 more)

### Community 21 - "src/marketdata/reconciliation.py"
Cohesion: 0.06
Nodes (8): candle_fingerprint(), exact_decimal_text(), reconcile(), ReconcileKey, ReconcileRequest, revision_summary(), DestinationWriter, ReplicationError

### Community 22 - "marketdata-fastapi-v1.1.0rc1/src/marketdata/reconciliation.py"
Cohesion: 0.06
Nodes (8): candle_fingerprint(), exact_decimal_text(), reconcile(), ReconcileKey, ReconcileRequest, revision_summary(), DestinationWriter, ReplicationError

### Community 23 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/reconciliation.py"
Cohesion: 0.06
Nodes (8): candle_fingerprint(), exact_decimal_text(), reconcile(), ReconcileKey, ReconcileRequest, revision_summary(), DestinationWriter, ReplicationError

### Community 24 - "qualify_v11_pipeline.py"
Cohesion: 0.09
Nodes (11): arguments(), database_url(), percentiles(), task_database(), expected_stop(), database_evidence(), main(), measurements() (+3 more)

### Community 25 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/providers/databento.py"
Cohesion: 0.05
Nodes (6): DatabentoProvider, fixed_price(), parse_mbp1(), DatabentoProvider, fixed_price(), parse_mbp1()

### Community 26 - "Store"
Cohesion: 0.06
Nodes (9): append_events(), decode_watermark(), encode_watermark(), event_page(), persisted_snapshot(), validate_watermark(), order_ns(), Store (+1 more)

### Community 27 - "test_candle_pipeline.py"
Cohesion: 0.08
Nodes (24): no_receiver_leaks(), pipeline(), test_auth_send_disconnect_is_measured_and_reduces_window(), connect(), test_auth_send_timeout_retains_owned_socket_for_bounded_cleanup(), test_bounded_window_large_universe_exact_routing(), test_connect_rejection_backs_off_without_creating_more_connections(), test_diagnostics_distinguish_raw_target_from_completion_filter() (+16 more)

### Community 28 - "tests/test_api_v1.py"
Cohesion: 0.10
Nodes (27): api_client(), assert_chart_types(), brokers(), candle(), persist(), test_all_native_intervals_exact_readback_null_volume(), test_bulk_100_sources_constant_query_count(), test_bulk_latest_quote_candle_unavailable_and_source_independence() (+19 more)

### Community 29 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/source_capture.py"
Cohesion: 0.10
Nodes (10): append_candles(), CaptureBackpressure, CaptureConflict, clock(), field_observation(), merge_fields(), prepare_quotes(), SourceCapture (+2 more)

### Community 30 - "src/marketdata/source_capture.py"
Cohesion: 0.10
Nodes (10): append_candles(), CaptureBackpressure, CaptureConflict, clock(), field_observation(), merge_fields(), prepare_quotes(), SourceCapture (+2 more)

### Community 31 - "TsetmcWriter"
Cohesion: 0.28
Nodes (3): parsed(), timestamp(), TsetmcWriter

### Community 32 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/api.py"
Cohesion: 0.10
Nodes (14): Candle, CandlePage, Command, candles(), latest(), latest_prices(), ticks(), decode_cursor() (+6 more)

### Community 34 - "src/marketdata/ingest_api.py"
Cohesion: 0.05
Nodes (26): body(), create_app(), admit_session(), handler(), endpoint(), http_error(), ingestion_openapi(), references() (+18 more)

### Community 35 - "CODEX.md"
Cohesion: 0.05
Nodes (39): 10. Futures, 11. Normalized tick model, 12. Financial numeric handling, 14. Ingestion architecture, 15. Database persistence, 17. TimescaleDB, 18. Latest-price state, 19. Price semantics (+31 more)

### Community 36 - "test_destination_ingestion.py"
Cohesion: 0.12
Nodes (22): candle(), record(), test_authoritative_transfer_is_fenced_and_serialized_with_inflight_commit(), test_batch_replay_conflict_and_cross_batch_observation_identity(), test_concurrent_duplicate_and_overlapping_requests(), test_correction_versions_noops_and_old_receipts_cannot_regress(), test_coverage_snapshots_backfill_unknown_bridges_and_actual_bars(), test_cross_producer_quote_uuid_collision_is_an_explicit_conflict() (+14 more)

### Community 37 - "MarketDataProvider"
Cohesion: 0.09
Nodes (5): MarketDataProvider, PermanentConnectionError, PermanentProviderError, ProviderHealth, SymbolHealth

### Community 38 - "MarketDataProvider"
Cohesion: 0.09
Nodes (5): MarketDataProvider, PermanentConnectionError, PermanentProviderError, ProviderHealth, SymbolHealth

### Community 39 - "MarketDataProvider"
Cohesion: 0.09
Nodes (5): MarketDataProvider, PermanentConnectionError, PermanentProviderError, ProviderHealth, SymbolHealth

### Community 40 - "MarketDataProvider"
Cohesion: 0.09
Nodes (5): MarketDataProvider, PermanentConnectionError, PermanentProviderError, ProviderHealth, SymbolHealth

### Community 41 - "test_candle_reliability.py"
Cohesion: 0.15
Nodes (17): setup(), test_backfill_provenance_survives_late_correction(), test_corrections_idempotent_audited_and_roll_up(), test_db_read_outage_recovery_uses_actual_state(), test_db_write_failure_never_acknowledged_before_success(), test_first_last_and_database_timings_are_separate(), slow_write(), test_historical_reconciliation_proves_partitions() (+9 more)

### Community 42 - "marketdata-fastapi/src/marketdata/providers/candle_pool.py"
Cohesion: 0.05
Nodes (13): CandleConnectionPool, collect(), PoolLimits, RequestBudget, retry_after_seconds(), Worker, test_access_denied_does_not_retry(), test_invalid_retry_after_uses_minimum() (+5 more)

### Community 43 - "_create_app"
Cohesion: 0.16
Nodes (18): _create_app(), database_error(), error_response(), health(), http_error(), instrument(), instruments(), latest_symbol() (+10 more)

### Community 45 - "Milestone 3B: independent durable HTTPS worker"
Cohesion: 0.06
Nodes (31): Batch envelope and canonical values, Company ingestion protocol v1 (FastAPI v1.1, milestone 2), Limits and errors, Receipts and retry policy, Routes, Session and ownership fencing, Transport and authentication, Company ingestion runtime — milestones 2, 2.1 and 3B (+23 more)

### Community 46 - "Milestone 3B: independent durable HTTPS worker"
Cohesion: 0.06
Nodes (31): Batch envelope and canonical values, Company ingestion protocol v1 (FastAPI v1.1, milestone 2), Limits and errors, Receipts and retry policy, Routes, Session and ownership fencing, Transport and authentication, Company ingestion runtime — milestones 2, 2.1 and 3B (+23 more)

### Community 48 - "test_session_recovery.py"
Cohesion: 0.14
Nodes (22): transfer(), expire(), new_credential(), replacement(), state(), test_actual_tls_ingestion_process_kill_and_restart_during_recovery(), start(), test_authenticated_other_producer_cannot_recover_someone_elses_streams() (+14 more)

### Community 49 - "test_ingest_http.py"
Cohesion: 0.10
Nodes (15): ingress(), test_body_streaming_record_limits_and_timeout_rolls_back(), held(), test_captured_status_projection_is_source_specific_and_expires(), test_coverage_http_identity_authorization_concurrency_and_backpressure(), test_global_rate_limit_across_instances_and_restart(), test_http_atomic_retry_conflict_lost_ack_and_server_restart(), test_https_auth_cross_role_and_sanitized_validation() (+7 more)

### Community 50 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/domain.py"
Cohesion: 0.12
Nodes (13): AssetClass, DataStatus, from_ns(), Instrument, InstrumentType, Model, normalize(), parse_timestamp_ns() (+5 more)

### Community 51 - "marketdata-fastapi/src/marketdata/domain.py"
Cohesion: 0.12
Nodes (13): AssetClass, DataStatus, from_ns(), Instrument, InstrumentType, Model, normalize(), parse_timestamp_ns() (+5 more)

### Community 52 - "marketdata-fastapi-v1.1.0rc1/src/marketdata/domain.py"
Cohesion: 0.12
Nodes (13): AssetClass, DataStatus, from_ns(), Instrument, InstrumentType, Model, normalize(), parse_timestamp_ns() (+5 more)

### Community 53 - "src/marketdata/domain.py"
Cohesion: 0.12
Nodes (13): AssetClass, DataStatus, from_ns(), Instrument, InstrumentType, Model, normalize(), parse_timestamp_ns() (+5 more)

### Community 54 - "test_dual_ingestion.py"
Cohesion: 0.08
Nodes (10): eventually(), observer_module(), released_api(), test_dual_factory_keeps_both_registries_and_independent_health(), test_latest_only_atomic_retry_ordering_precision_and_no_history(), test_observer_never_qualifies_simulated_tradingview_prices(), test_observer_separates_source_time_delivery_and_missing_timestamps(), test_old_quote_stays_stale_across_released_api_restarts() (+2 more)

### Community 56 - "TsetmcError"
Cohesion: 0.09
Nodes (31): register(), endpoint(), upload(), revisions(), row(), clocks(), canonical(), decode() (+23 more)

### Community 57 - "test_native_candles.py"
Cohesion: 0.04
Nodes (19): test_fxcm_quote_namespace_normalization_keeps_identity_and_delay_gates(), test_two_broker_candles_and_volume_remain_independent_in_postgresql(), test_unclassified_source_volume_is_preserved_as_evidence_not_typed_or_additive(), test_all_captured_sessions_and_weekend(), test_compressed_sessions_cover_all_minutes_without_overlap(), test_timeout_is_visible_per_symbol_and_never_finalized(), live_harness(), test_guest_opt_in_keeps_worker_cap_and_default_guard() (+11 more)

### Community 58 - "test_dual_collector_to_exact_released_api_outage_recovery_replay"
Cohesion: 0.11
Nodes (5): BlockingCandles, paused_test_database(), QuoteSocket, test_dual_collector_to_exact_released_api_outage_recovery_replay(), quote_connect()

### Community 59 - "README.md"
Cohesion: 0.15
Nodes (9): Authentication remains PROVISIONAL, Final validation, Inspected baseline and resulting contract, Journal correctness and recovery, Limits and failure checks, Remaining limitations and next actions, Batch 4 measured API performance, Historical README (before native installation) (+1 more)

### Community 60 - "Store"
Cohesion: 0.07
Nodes (4): order_ns(), Store, tick_record(), project_status()

### Community 61 - "src/marketdata/providers/tradingview_candles.py"
Cohesion: 0.13
Nodes (3): parse_bar(), TradingViewCandleProvider, validate_source()

### Community 63 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/candle_ingestion.py"
Cohesion: 0.11
Nodes (4): CandleIngestion, watch_overrun(), CandleStore, is_backfill()

### Community 64 - "src/marketdata/candle_ingestion.py"
Cohesion: 0.11
Nodes (4): CandleIngestion, watch_overrun(), CandleStore, is_backfill()

### Community 65 - "test_process_separation.py"
Cohesion: 0.11
Nodes (12): forbidden(), test_actual_select_only_role_serves_api(), test_api_reads_persisted_identity_history_without_source_access(), test_api_websocket_explicitly_unavailable(), test_collector_metrics_listener_closes_on_shutdown(), test_collector_ownership_loss_stops_owned_tasks(), test_collector_runner_graceful_shutdown(), test_database_connection_loss_returns_503_then_recovers() (+4 more)

### Community 66 - "src/marketdata/providers/candle_pool.py"
Cohesion: 0.12
Nodes (3): PoolLimits, RequestBudget, Worker

### Community 67 - "marketdata-fastapi/src/marketdata/candle_ingestion.py"
Cohesion: 0.11
Nodes (4): CandleIngestion, watch_overrun(), CandleStore, is_backfill()

### Community 68 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/events.py"
Cohesion: 0.18
Nodes (6): append_events(), decode_watermark(), encode_watermark(), event_page(), persisted_snapshot(), validate_watermark()

### Community 70 - "test_tsetmc_ingestion.py"
Cohesion: 0.12
Nodes (32): reconcile(), commit(), current(), quality_state(), rehash(), request(), test_administrative_fences_do_not_rewrite_imports(), test_alias_barriers_do_not_cross_instrument_epochs() (+24 more)

### Community 71 - "create_app"
Cohesion: 0.14
Nodes (15): body(), create_app(), admit_session(), handler(), endpoint(), http_error(), invalid_request(), receipt() (+7 more)

### Community 72 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/providers/oanda.py"
Cohesion: 0.12
Nodes (3): bounded_lines(), OandaProvider, parse_price()

### Community 73 - "src/marketdata/providers/oanda.py"
Cohesion: 0.12
Nodes (3): bounded_lines(), OandaProvider, parse_price()

### Community 74 - "record"
Cohesion: 0.27
Nodes (13): check_database(), main(), private(), server(), commit(), recover(), session(), worker() (+5 more)

### Community 75 - "fastapi-v1.1-milestone5.md"
Cohesion: 0.05
Nodes (29): Controlled legacy collector transition and later laptop-to-server handover, Linux collector and worker installation, Windows collector and worker installation, Controlled release / site acceptance checklist, Credential rotation and failed release rollback, Destination backup and restore, Monitoring and proposed alerts, Operations, backup/restore, reconciliation and application rollback (+21 more)

### Community 76 - "logging"
Cohesion: 0.12
Nodes (12): configure_logging(), JsonFormatter, Metrics, configure_logging(), JsonFormatter, Metrics, configure_logging(), JsonFormatter (+4 more)

### Community 77 - "Pipeline"
Cohesion: 0.09
Nodes (18): run(), business_registry(), free_port(), main(), Pipeline, corrected(), history_delivered(), locally_committed() (+10 more)

### Community 78 - "make_pool"
Cohesion: 0.18
Nodes (21): clean(), jobs(), make_pool(), run(), test_bounds_reject_duplicate_overflow_and_wrong_identity(), test_cancellation_joins_all_tasks_and_releases_capacity(), test_cleanup_deadline_blocks_replacement_connections(), test_completed_native_missing_bar_is_success_not_transport_error() (+13 more)

### Community 79 - "test_ingestion.py"
Cohesion: 0.14
Nodes (11): BadCredentials, DisconnectOnce, service(), test_monitor_records_application_loop_lag_and_stops_with_service(), test_outage_retains_batch_and_receive_does_not_block(), test_permanent_failure_does_not_stop_other_provider(), test_queue_full_is_visible_and_shutdown_drains(), test_reconnect_restores_subscriptions() (+3 more)

### Community 80 - "test_providers.py"
Cohesion: 0.09
Nodes (5): FakeSocket, test_binance_malformed_and_sequence_gap(), test_binance_trade_fixture(), test_mock_multi_instrument_stream_and_disconnect(), test_oanda_authentication_not_retried()

### Community 82 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/api_v1.py"
Cohesion: 0.22
Nodes (14): completed_candle(), create_router(), candles(), coverage(), dashboard_candles(), health(), instruments(), latest_candles() (+6 more)

### Community 83 - "Store"
Cohesion: 0.07
Nodes (4): order_ns(), Store, tick_record(), project_status()

### Community 84 - "pytest"
Cohesion: 0.04
Nodes (34): test_browser_recovery_example(), test_binary_float_input_rejected(), test_configuration_validation(), test_contract_parser_does_not_guess_century(), test_future_requires_concrete_contract(), test_history_cursor_and_window(), test_mock_cannot_claim_realtime(), test_naive_timestamps_rejected() (+26 more)

### Community 85 - "probe_native_history.py"
Cohesion: 0.14
Nodes (3): Capture, idle(), run()

### Community 87 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/collector.py"
Cohesion: 0.13
Nodes (4): Collector, collector_lifespan(), main(), run_collector()

### Community 88 - "marketdata-fastapi-v1.1.0rc1/src/marketdata/candles.py"
Cohesion: 0.21
Nodes (4): expected_minute(), MarketCandle, minute_start(), next_collection()

### Community 89 - "uuid"
Cohesion: 0.05
Nodes (3): benchmark(), main(), main()

### Community 90 - "create_app"
Cohesion: 0.18
Nodes (12): body(), create_app(), admit_session(), handler(), endpoint(), receipt(), reconcile_state(), recover() (+4 more)

### Community 93 - "test_databento_sdk.py"
Cohesion: 0.11
Nodes (7): definition(), FakeClient, record(), test_adapter_checks_real_definitions_before_ticks(), test_adapter_rejects_wrong_expiry(), test_bare_sdk_disconnect_is_retryable(), test_definition_import_rejects_options_and_missing_maturity()

### Community 95 - "marketdata-fastapi-v1.1.0rc1/src/marketdata/api_models.py"
Cohesion: 0.17
Nodes (16): ChartData, CompletedCandle, CoverageItem, CoveragePage, ErrorBody, ErrorResponse, GapRange, HistoricalCandlePage (+8 more)

### Community 97 - "marketdata-fastapi/src/marketdata/api_models.py"
Cohesion: 0.17
Nodes (16): ChartData, CompletedCandle, CoverageItem, CoveragePage, ErrorBody, ErrorResponse, GapRange, HistoricalCandlePage (+8 more)

### Community 98 - "src/marketdata/api_models.py"
Cohesion: 0.17
Nodes (16): ChartData, CompletedCandle, CoverageItem, CoveragePage, ErrorBody, ErrorResponse, GapRange, HistoricalCandlePage (+8 more)

### Community 99 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/api_models.py"
Cohesion: 0.17
Nodes (16): ChartData, CompletedCandle, CoverageItem, CoveragePage, ErrorBody, ErrorResponse, GapRange, HistoricalCandlePage (+8 more)

### Community 100 - "Market Data REST and WebSocket API v1"
Cohesion: 0.10
Nodes (19): Authentication and browser access, Common contracts and limits, Completed historical candles, Coverage, Dedicated read-only database role, Endpoint inventory and compatibility, Frontend and server examples, Go dashboard candle compatibility (+11 more)

### Community 102 - "SyncWorker"
Cohesion: 0.06
Nodes (20): run(), SyncWorker, work(), chart_data(), completed_candle(), create_router(), candles(), coverage() (+12 more)

### Community 103 - "test_health_api.py"
Cohesion: 0.15
Nodes (3): test_health_serialization_and_latest_receipt_freshness(), Clock, clock()

### Community 104 - "marketdata-fastapi-v1.1.0rc1/src/marketdata/api_v1.py"
Cohesion: 0.12
Nodes (16): completed_candle(), create_router(), candles(), coverage(), dashboard_candles(), health(), instruments(), latest_candles() (+8 more)

### Community 105 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/sample_data.py"
Cohesion: 0.12
Nodes (9): Settings, main(), prepare_reader(), publish_quotes(), run(), sample_registry(), SampleSettings, seed_history() (+1 more)

### Community 106 - "Current state - 2026-10-20, M3B-2 integration checkpoint"
Cohesion: 0.15
Nodes (12): Archived handoff before workspace cleanup, Commercial production/test preparation, Current state - 2026-10-20, M3B-2 integration checkpoint, Deployment and next actions, Developer handoff audit, FastAPI v1.1 - Milestone 5 complete, publication authorized, Prior dual TradingView collector qualification — schema 0006, Prior frozen rc1 evidence (historical) (+4 more)

### Community 107 - "marketdata-fastapi/src/marketdata/sample_data.py"
Cohesion: 0.19
Nodes (7): prepare_reader(), publish_quotes(), run(), sample_registry(), SampleSettings, seed_history(), validate_target()

### Community 108 - "src/marketdata/sample_data.py"
Cohesion: 0.19
Nodes (7): prepare_reader(), publish_quotes(), run(), sample_registry(), SampleSettings, seed_history(), validate_target()

### Community 110 - "test_release_foundation.py"
Cohesion: 0.13
Nodes (6): test_actual_destination_source_boundary(), test_destination_snapshot_persists_without_source_modules(), test_guarded_first_install_from_separate_tracks(), test_initial_provisioning_rejects_transfer_and_rolls_back(), test_release_rejects_role_before_loading_secrets(), test_source_boundary_and_new_collector_writer_permissions()

### Community 111 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/providers/tradingview.py"
Cohesion: 0.05
Nodes (11): CandleConnectionPool, collect(), PoolLimits, RequestBudget, retry_after_seconds(), Worker, encode_message(), FrameDecoder (+3 more)

### Community 113 - "test_integration_compatibility.py"
Cohesion: 0.09
Nodes (9): test_default_legacy_selection_prefers_fresh_quote_and_newer_stale_candle(), test_native_tick_volume_keeps_its_units_and_rollup_does_not_sum_it(), test_real_connection_failure_and_server_statement_timeout(), test_real_http_workers_read_stored_broker_candles_without_collector(), seed_brokers(), snapshot(), test_0004_upgrade_and_status_only_rollback_preserve_all_market_rows(), test_broker_api_reads_during_independent_recovery_keep_quotes_and_gaps_separate() (+1 more)

### Community 114 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/collector.py"
Cohesion: 0.13
Nodes (4): Collector, collector_lifespan(), main(), run_collector()

### Community 115 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/ingest_auth.py"
Cohesion: 0.14
Nodes (6): Credential, Credentials, Principal, session(), SessionRequest, strict_json()

### Community 116 - "pydantic"
Cohesion: 0.08
Nodes (13): Grant, boundary(), execute(), provision(), setup(), InstrumentBinding, provision(), register() (+5 more)

### Community 118 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/providers/factory.py"
Cohesion: 0.07
Nodes (4): build_providers(), tradingview_provider(), build_providers(), tradingview_provider()

### Community 119 - "decimal"
Cohesion: 0.06
Nodes (6): definition_entry(), is_snapshot(), materialize(), Request, is_snapshot(), materialize()

### Community 120 - "observe_dual_ingestion.py"
Cohesion: 0.21
Nodes (3): main(), observe(), summarize()

### Community 121 - "qualify_api.py"
Cohesion: 0.14
Nodes (3): load(), qualify(), summary()

### Community 122 - "marketdata-fastapi-v1.1.0rc1/src/marketdata/events.py"
Cohesion: 0.18
Nodes (6): append_events(), decode_watermark(), encode_watermark(), event_page(), persisted_snapshot(), validate_watermark()

### Community 123 - "marketdata-fastapi/src/marketdata/sessions.py"
Cohesion: 0.30
Nodes (4): classify_ranges(), Expectation, expectation(), session_windows()

### Community 126 - "src/marketdata/cli.py"
Cohesion: 0.16
Nodes (5): discover_oanda(), import_databento(), main(), oanda_entry(), write_registry()

### Community 128 - "retrieve"
Cohesion: 0.29
Nodes (8): retrieve(), current_generation(), dispatch(), error_seen(), receive(), release(), remember(), send()

### Community 129 - "marketdata-fastapi-v1.1.0rc1/src/marketdata/ingest_auth.py"
Cohesion: 0.15
Nodes (6): Credential, Credentials, Principal, session(), SessionRequest, strict_json()

### Community 130 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/cli.py"
Cohesion: 0.16
Nodes (5): discover_oanda(), import_databento(), main(), oanda_entry(), write_registry()

### Community 133 - "src/marketdata/ws_models.py"
Cohesion: 0.17
Nodes (11): CandleEvent, ChangePage, Envelope, Heartbeat, MarketCommand, PriceEvent, PriceSnapshot, SocketError (+3 more)

### Community 134 - "marketdata-fastapi/src/marketdata/ws_models.py"
Cohesion: 0.17
Nodes (11): CandleEvent, ChangePage, Envelope, Heartbeat, MarketCommand, PriceEvent, PriceSnapshot, SocketError (+3 more)

### Community 135 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/ws_models.py"
Cohesion: 0.17
Nodes (11): CandleEvent, ChangePage, Envelope, Heartbeat, MarketCommand, PriceEvent, PriceSnapshot, SocketError (+3 more)

### Community 136 - "src/marketdata/events.py"
Cohesion: 0.18
Nodes (6): append_events(), decode_watermark(), encode_watermark(), event_page(), persisted_snapshot(), validate_watermark()

### Community 137 - "marketdata-fastapi-v1.1.0rc1/src/marketdata/ws_models.py"
Cohesion: 0.17
Nodes (11): CandleEvent, ChangePage, Envelope, Heartbeat, MarketCommand, PriceEvent, PriceSnapshot, SocketError (+3 more)

### Community 138 - "FastAPI v1.1 — Milestone 4 verification"
Cohesion: 0.11
Nodes (15): Actual passing tests and separate skips, Evidence levels and environment, Failure recovery, ownership and reconciliation, FastAPI v1.1 — Milestone 4 verification, Financial results and trace examples, Measured workload and proposed service targets, Narrow corrective change and changed files, Preservation, exit gate and remaining release work (+7 more)

### Community 141 - "marketdata-fastapi/tests/browser-marketdata.test.mjs"
Cohesion: 0.08
Nodes (7): Socket, MarketDataClient, Socket, calls, client, international, iran

### Community 142 - "Replay"
Cohesion: 0.07
Nodes (16): test_overrun_reported_once_and_does_not_spawn_another_cycle(), test_health_reopening_counts_only_expected_minutes_and_clock_regression(), test_activation_restart_recovery_removal_and_source_identity(), test_pool_configuration_rejects_unusable_or_out_of_scope_limits(), test_restart_before_first_collection_recovers_from_activation(), Replay, test_candle_database_retry_preserves_bounded_batch(), test_candle_upsert_latest_rollup_and_unsupported_backfill() (+8 more)

### Community 143 - "marketdata-fastapi-v1.1.0rc1/src/marketdata/session_recovery.py"
Cohesion: 0.15
Nodes (4): recover_session(), RecoveryReceipt, RecoveryRequest, RecoveryStream

### Community 144 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/session_recovery.py"
Cohesion: 0.15
Nodes (4): recover_session(), RecoveryReceipt, RecoveryRequest, RecoveryStream

### Community 145 - "make_provider"
Cohesion: 0.32
Nodes (11): make_provider(), observe_all(), quote_for(), test_connected_heartbeats_without_market_data_degrade(), test_last_time_and_decimal_preserved_without_inventing_trade_sizes(), test_non_realtime_quotes_never_emitted_and_other_symbols_continue(), test_one_stale_symbol_recovery_and_metrics(), test_product_specific_freshness_and_configuration() (+3 more)

### Community 146 - "CandleConnectionPool"
Cohesion: 0.16
Nodes (3): CandleConnectionPool, collect(), retry_after_seconds()

### Community 147 - "math"
Cohesion: 0.11
Nodes (6): json_value(), PendingUpload, retry_delay(), single_instance(), sync_directory(), test_durable_upload_retry_and_receipt_validation()

### Community 149 - "Socket"
Cohesion: 0.20
Nodes (6): Socket, test_health_requires_observations_not_handshake(), connection(), test_protocol_errors_require_operator_intervention(), test_reconnect_restores_subscriptions_and_revalidates_status(), connection()

### Community 150 - "install_marketdata_proxy"
Cohesion: 0.17
Nodes (8): install_marketdata_proxy(), allowed(), rest(), websocket_proxy(), session(), test_provisional_adapter_denies_invalid_origin_or_missing_cookie_before_upstream(), test_provisional_cookie_adapter_relays_rest_ws_and_revoked_session_closes(), simulated_session()

### Community 151 - "src/marketdata/session_recovery.py"
Cohesion: 0.15
Nodes (4): recover_session(), RecoveryReceipt, RecoveryRequest, RecoveryStream

### Community 153 - "Standalone Market Data FastAPI"
Cohesion: 0.22
Nodes (9): Disposable Docker setup, Database and external-producer integration contract, Disposable Docker quick start (PowerShell), Independent install, start and deploy, Repository recommendation and handover limits, REST and WebSocket examples, Standalone FastAPI backend, rss() (+1 more)

### Community 155 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/candles.py"
Cohesion: 0.21
Nodes (4): expected_minute(), MarketCandle, minute_start(), next_collection()

### Community 156 - "test_api_production.py"
Cohesion: 0.15
Nodes (5): test_liveness_survives_database_failure_without_credentials(), failed(), test_production_refuses_owner_dsn_and_accepts_select_only_role(), test_runtime_metrics_and_health_observe_idle_and_failed_reader(), test_unexpected_error_and_auth_metrics_never_log_sensitive_text()

### Community 157 - "marketdata-fastapi/src/marketdata/candles.py"
Cohesion: 0.21
Nodes (4): expected_minute(), MarketCandle, minute_start(), next_collection()

### Community 158 - "src/marketdata/candles.py"
Cohesion: 0.21
Nodes (4): expected_minute(), MarketCandle, minute_start(), next_collection()

### Community 159 - "install_marketdata_proxy"
Cohesion: 0.24
Nodes (5): install_marketdata_proxy(), allowed(), rest(), websocket_proxy(), session()

### Community 161 - "decimal"
Cohesion: 0.10
Nodes (7): chart(), history(), Batch, float64(), SimpleStore, unpack(), native_store()

### Community 163 - "FastAPI Batch 2 — completion report"
Cohesion: 0.13
Nodes (15): 10. Exact test results, 11. Performance measurements, 12. Exact local commands, 13. Remaining frontend integration, 14. Authorization/deployment issues, 1. Existing functionality reused, 2. New routes implemented, 3. Backward compatibility (+7 more)

### Community 164 - "marketdata-fastapi/tests/conftest.py"
Cohesion: 0.29
Nodes (5): database_url(), pair(), readonly_database_url(), registry(), store()

### Community 165 - "urllib_parse"
Cohesion: 0.03
Nodes (7): launch(), main(), test_sample_history_readonly_api_and_live_replay_without_collector(), test_sample_writer_rejects_non_disposable_targets_before_connect(), paused(), test_sample_history_readonly_api_and_live_replay_without_collector(), test_sample_writer_rejects_non_disposable_targets_before_connect()

### Community 166 - "TSETMC M3B-2 company INGEST and storage"
Cohesion: 0.08
Nodes (23): Boundaries and defaults, Destination migration 0011, Explicit administration and role upgrades (future operator action), Modules and shared components, Reconciliation and legacy READ isolation, Release prerequisites, Boundaries and remaining gates, Corrected invariants (+15 more)

### Community 168 - "test_recovery_fanout.py"
Cohesion: 0.15
Nodes (3): NoLinearSearch, test_large_recovery_acknowledgements_keep_fanout_exact_without_linear_search(), write_candles()

### Community 169 - "socket"
Cohesion: 0.04
Nodes (14): bff_server(), main(), initialize(), main(), main(), main(), bff_server(), test_provisional_adapter_denies_invalid_origin_or_missing_cookie_before_upstream() (+6 more)

### Community 170 - "Batch 4 employer qualification report — 2026-10-14"
Cohesion: 0.14
Nodes (14): 10. Failure/recovery — VERIFIED deterministic scope, 11–13. Deployment, rollback and frontend handoff — PARTIALLY VERIFIED, 14. Executed validation — VERIFIED, 15. Remaining blockers and audit decisions, 1. Exact supported endpoints — VERIFIED, 2. Authentication — VERIFIED locally / production integration PARTIALLY VERIFIED, 3. Historical data — VERIFIED, 4. Current prices — PARTIALLY VERIFIED (+6 more)

### Community 171 - "FastAPI v1.1 integration — Phase A audit and design"
Cohesion: 0.14
Nodes (13): 10. File-by-file implementation plan and milestones, 11. Acceptance and evidence plan, 12. Verification actually executed in Phase A, 1. Verified version and deployment boundaries, 2. Source-to-destination compatibility matrix, 3. Writer and ordering findings, 4. Independent quote qualification, 5. Recommended architecture (+5 more)

### Community 172 - "strict_json"
Cohesion: 0.15
Nodes (6): Credential, Credentials, Principal, session(), SessionRequest, strict_json()

### Community 173 - "dataclasses"
Cohesion: 0.09
Nodes (3): Fanout, Subscriber, Request

### Community 174 - "destination"
Cohesion: 0.22
Nodes (3): Reproduction (isolated only), destination(), test_populated_0007_runtime_upgrade_and_roundtrip()

### Community 178 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/sessions.py"
Cohesion: 0.27
Nodes (4): classify_ranges(), Expectation, expectation(), session_windows()

### Community 179 - "marketdata-fastapi-v1.1.0rc1/src/marketdata/sessions.py"
Cohesion: 0.27
Nodes (4): classify_ranges(), Expectation, expectation(), session_windows()

### Community 180 - "Experimental TradingView guest market data"
Cohesion: 0.15
Nodes (13): Collection and storage, Commercial access for this installation, Experimental TradingView guest market data, Inspect stored data, Native one-minute candle storage, Optional raw-history maintenance, Protocol evidence and maintenance, Real-time gate and tick semantics (+5 more)

### Community 183 - "marketdata-fastapi-v1.1.0rc1/src/marketdata/price_selection.py"
Cohesion: 0.30
Nodes (3): observation_age(), select_price(), stale_threshold()

### Community 184 - "Live guest candles through PostgreSQL"
Cohesion: 0.18
Nodes (9): Candle hardening verification - 2026-10-07, Historical truth observed live, Latency diagnosis and measurement, Reliability verdicts, Completed paced run, Evidence and interpretation, Initial unpaced result, Live guest candles through PostgreSQL (+1 more)

### Community 185 - "marketdata-collector-sync-v1.1.0rc1/src/marketdata/price_selection.py"
Cohesion: 0.30
Nodes (3): observation_age(), select_price(), stale_threshold()

### Community 186 - "src/marketdata/price_selection.py"
Cohesion: 0.30
Nodes (3): observation_age(), select_price(), stale_threshold()

### Community 187 - "marketdata-fastapi/src/marketdata/price_selection.py"
Cohesion: 0.30
Nodes (3): observation_age(), select_price(), stale_threshold()

### Community 188 - "startMarketData"
Cohesion: 0.41
Nodes (11): startMarketData(), apply(), get(), open(), putCandle(), recover(), refreshCoverage(), refreshHistory() (+3 more)

### Community 189 - "datetime"
Cohesion: 0.04
Nodes (5): main(), plan_summary(), visit(), timing(), run()

### Community 190 - "startMarketData"
Cohesion: 0.41
Nodes (11): startMarketData(), apply(), get(), open(), putCandle(), recover(), refreshCoverage(), refreshHistory() (+3 more)

### Community 192 - "startMarketData"
Cohesion: 0.41
Nodes (11): startMarketData(), apply(), get(), open(), putCandle(), recover(), refreshCoverage(), refreshHistory() (+3 more)

### Community 193 - "Market Data REST and WebSocket API v1"
Cohesion: 0.10
Nodes (19): Authentication and browser access, Common contracts and limits, Completed historical candles, Coverage, Dedicated read-only database role, Endpoint inventory and compatibility, Frontend and server examples, Go dashboard candle compatibility (+11 more)

### Community 194 - "src/marketdata/sessions.py"
Cohesion: 0.30
Nodes (4): classify_ranges(), Expectation, expectation(), session_windows()

### Community 195 - "Configurable candle connection pool"
Cohesion: 0.17
Nodes (12): Architecture and ownership, Availability, failure recovery and live boundary, Configurable candle connection pool, Diagnostics and benchmark method, Evidence, Final independent-response comparison, Final validation and rollout, Interpretation and rejected conclusions (+4 more)

### Community 196 - "Native candle retrieval scalability"
Cohesion: 0.17
Nodes (12): Capacity, deadlines and overload policy, Initial live probes: escalation stopped, Lifecycle, persistence and restoration, Native candle retrieval scalability, Persistence benchmark, Previous task: normal-collector live observation, Protocol evidence and architecture, Reproducible commands (+4 more)

### Community 197 - "startMarketData"
Cohesion: 0.41
Nodes (11): startMarketData(), apply(), get(), open(), putCandle(), recover(), refreshCoverage(), refreshHistory() (+3 more)

### Community 198 - "retrieve"
Cohesion: 0.23
Nodes (10): window(), receiver(), retrieve(), current_generation(), dispatch(), error_seen(), receive(), release() (+2 more)

### Community 199 - "Production deployment and recovery"
Cohesion: 0.33
Nodes (6): Backup, restore and rollback, Configuration and secrets, Database principals and migrations, Health and monitoring, HTTPS, networking and logs, Production deployment and recovery

### Community 200 - "Shared dashboard integration on audited company storage"
Cohesion: 0.22
Nodes (7): Frontend, Qualification limits, Setup, Shared dashboard integration on audited company storage, Checkpoints, Local files, Workspace and recovery checkpoints

### Community 201 - "test_actual_pytest_fixture_dependency_order"
Cohesion: 0.06
Nodes (12): owned(), close(), connect(), test_actual_pytest_fixture_dependency_order(), verify(), test_shared_fixture_guard_finishes_before_any_store_write(), register(), verify() (+4 more)

### Community 202 - ".__call__"
Cohesion: 0.12
Nodes (5): http_error(), invalid_request(), failure(), IngestGuard, guarded_send()

### Community 204 - "smoke_production_tradingview.py"
Cohesion: 0.15
Nodes (4): main(), reconcile(), smoke(), validate_candle()

### Community 206 - "test_watchdog_uses_owned_runner_to_reconnect_and_restore"
Cohesion: 0.22
Nodes (4): test_conflicting_source_metadata_rejected(), test_decoder_rejects_corrupt_or_excessive_lengths(), test_watchdog_uses_owned_runner_to_reconnect_and_restore(), __init__()

### Community 210 - "Employer business universe — provisional qualification, 2026-10-13"
Cohesion: 0.18
Nodes (11): Approval decisions and safe activation plan, Binance selection, Duration, latency and simultaneous capacity, Employer business universe — provisional qualification, 2026-10-13, Evidence and reproducibility, Forex identity and default display, Gaps and recovery investigation, Measured business coverage (+3 more)

### Community 211 - "Milestone 3B: independent durable HTTPS worker"
Cohesion: 0.18
Nodes (11): Capacity and monitoring, Delivery, retries and recovery, Destination ordering and actual-state evidence, Enrollment, coverage, status and fairness, Linux service, Local durable state, locks and permissions, Milestone 3B: independent durable HTTPS worker, Reconciliation, restore and continuity (+3 more)

### Community 212 - "collector"
Cohesion: 0.29
Nodes (3): collector(), providers(), InjectedCandles

### Community 215 - "AGENTS.md"
Cohesion: 0.18
Nodes (9): Architecture, Change discipline, Core invariants, Documentation, graphify, Handoff, Purpose, Required context (+1 more)

### Community 223 - "FastAPI v1.1 — milestone 1 destination foundation"
Cohesion: 0.18
Nodes (10): Actual migration, Changed files and rationale, Compatibility of existing callers, FastAPI v1.1 — milestone 1 destination foundation, Remaining risks and next scope, Reproduction on disposable infrastructure, Scope and decisions, Transaction and replay behavior (+2 more)

### Community 224 - "Platform reference"
Cohesion: 0.20
Nodes (10): APIs, Architecture and reliability, Configuration and live activation, Database, timestamps and candles, Identity and futures rollover, Ordinary expanded candle pilot, Platform reference, Provider coverage (+2 more)

### Community 228 - "test_candle_pool_benchmark.py"
Cohesion: 0.27
Nodes (6): args(), harness(), test_live_pool_fails_before_network(), test_permanent_source_omissions_are_not_falsely_recovered(), test_pool_benchmark_reports_beyond100_and_cleanup(), test_transient_deadline_failures_recover_with_bounded_history()

### Community 231 - "prices_socket"
Cohesion: 0.18
Nodes (7): authorized(), authenticate(), prices_socket(), commands(), send(), ticks_out(), marketdata_socket()

### Community 232 - "render_event"
Cohesion: 0.20
Nodes (3): create_stream_router(), changes(), render_event()

### Community 234 - "render_event"
Cohesion: 0.13
Nodes (5): create_stream_router(), changes(), marketdata_socket(), receiver(), render_event()

### Community 240 - "render_event"
Cohesion: 0.07
Nodes (6): create_stream_router(), changes(), marketdata_socket(), MarketClient, MarketHub, render_event()

### Community 241 - "Milestone 3A: local source capture and milestone 3B contract"
Cohesion: 0.25
Nodes (7): Candle atomicity and commit ordering, Exact milestone 3B local consumer interface, Latest prices: partial inputs, durable full snapshots, Milestone 3A: local source capture and milestone 3B contract, Separate source migration and activation, Storage, failure and restore policy, Verified source audit and compatibility matrix

### Community 242 - "cursor"
Cohesion: 0.09
Nodes (10): changes(), router(), daily(), latest(), socket(), snapshot(), connect(), test_cycle_uses_one_history_request_per_symbol_and_owns_cleanup() (+2 more)

### Community 243 - "test_production_tradingview_smoke.py"
Cohesion: 0.22
Nodes (3): test_smoke_failure_checkpoint_excludes_credentials(), test_smoke_reconciles_committed_ws_candle_and_rejects_changed_prices(), test_smoke_rejects_simulated_source_identity_and_forming_bars()

### Community 244 - "Milestone 3A: local source capture and milestone 3B contract"
Cohesion: 0.25
Nodes (7): Candle atomicity and commit ordering, Exact milestone 3B local consumer interface, Latest prices: partial inputs, durable full snapshots, Milestone 3A: local source capture and milestone 3B contract, Separate source migration and activation, Storage, failure and restore policy, Verified source audit and compatibility matrix

### Community 245 - "cursor"
Cohesion: 0.09
Nodes (24): Browser authentication (PROVISIONAL), Commands and subscription JSON, Delivery and cursor mechanics, Event JSON schemas, Initial snapshots and reconnect recovery, JavaScript use and isolated validation, Limits and slow consumers, WebSocket market data v1 (+16 more)

### Community 246 - "FastAPI Batch 1: independent processes"
Cohesion: 0.40
Nodes (5): Disposable validation and preservation, FastAPI Batch 1: independent processes, Health, REST and WebSocket contracts, Independent startup and shutdown, Rollback and next batches

### Community 247 - "Milestone 3A review: durable local capture"
Cohesion: 0.25
Nodes (7): Actual passing, skipped and not-run results, Implementation and changed files, Milestone 3A review: durable local capture, Remaining risks and recommended milestone 3B, Reproduce the full suites, Transaction, ordering and delivery guarantees, Verification method and preservation

### Community 248 - "Milestone 2.1 — secure same-producer session recovery"
Cohesion: 0.25
Nodes (8): Clock and freshness expectations, Durable client state transitions for milestone 3, Errors and backoff, Exact request and response, Milestone 2.1 — secure same-producer session recovery, Reproduce on isolated databases, Transaction and fencing, Windows and Linux HTTP examples

### Community 249 - "Milestone 3A: local source capture and milestone 3B contract"
Cohesion: 0.25
Nodes (7): Candle atomicity and commit ordering, Exact milestone 3B local consumer interface, Latest prices: partial inputs, durable full snapshots, Milestone 3A: local source capture and milestone 3B contract, Separate source migration and activation, Storage, failure and restore policy, Verified source audit and compatibility matrix

### Community 250 - "Ordinary TradingView collector: 100-source qualification"
Cohesion: 0.22
Nodes (8): Actual earlier ordinary measurements, Completed accuracy-selected 100 result, Current 100 configuration and acceptance, Deployment identity and exact activation / rollback, Fixed identities and activation, Interruption / recovery and the scoped outage fix, Ordinary TradingView collector: 100-source qualification, Verification

### Community 251 - "WebSocket market data v1"
Cohesion: 0.25
Nodes (8): Browser authentication (PROVISIONAL), Commands and subscription JSON, Delivery and cursor mechanics, Event JSON schemas, Initial snapshots and reconnect recovery, JavaScript use and isolated validation, Limits and slow consumers, WebSocket market data v1

### Community 252 - "Operations, backup/restore, reconciliation and application rollback"
Cohesion: 0.25
Nodes (7): Controlled release / site acceptance checklist, Credential rotation and failed release rollback, Destination backup and restore, Monitoring and proposed alerts, Operations, backup/restore, reconciliation and application rollback, Source backup, lost state and reconciliation, Startup, outage and terminal errors

### Community 253 - "provider"
Cohesion: 0.09
Nodes (34): Latest prices, Authentication and browser access, Common contracts and limits, Completed historical candles, Coverage, Dedicated read-only database role, Endpoint inventory and compatibility, Frontend and server examples (+26 more)

### Community 254 - "Company frontend handoff"
Cohesion: 0.40
Nodes (5): Authentication, Company frontend handoff, Requests and responses, Small standards-based example, WebSocket and reconnection

### Community 256 - "Native availability investigation — 2026-10-12"
Cohesion: 0.40
Nodes (5): BINANCE:ATOMUSDT, bucket starting 12:14 UTC, Changes and operations, Historical 128/256/512 evidence, Native availability investigation — 2026-10-12, Ordinary collector and recovery

### Community 257 - "WebSocket market data v1"
Cohesion: 0.25
Nodes (8): Browser authentication (PROVISIONAL), Commands and subscription JSON, Delivery and cursor mechanics, Event JSON schemas, Initial snapshots and reconnect recovery, JavaScript use and isolated validation, Limits and slow consumers, WebSocket market data v1

### Community 258 - "re"
Cohesion: 0.04
Nodes (35): boundary(), execute(), main(), provision(), boundary(), execute(), main(), provision() (+27 more)

### Community 262 - "Current state - native installation, 2026-10-22"
Cohesion: 0.50
Nodes (4): Current state - native installation, 2026-10-22, Native handshake recovery fix, Native recovery hardening, TSETMC validation qualification (2026-10-22)

### Community 263 - "FastAPI v1.1 — Milestone 3B review"
Cohesion: 0.29
Nodes (6): Changed files and rationale, FastAPI v1.1 — Milestone 3B review, Findings and implementation, Migration, permissions and concurrency, Preservation and remaining qualification, Verification interpretation

### Community 264 - "Ordinary collector instrument activation"
Cohesion: 0.29
Nodes (7): Activation and history, Configuration and ordinary execution, Git boundary, Live result — 2026-10-12, Measurement definitions, Ordinary collector instrument activation, Safe activation and rollback

### Community 265 - "Standalone Market Data FastAPI"
Cohesion: 0.10
Nodes (16): Authentication, Company frontend handoff, Requests and responses, Small standards-based example, WebSocket and reconnection, External database and producer integration, Current ChartData and PostgreSQL 16.1 qualification — 2026-10-14, Distribution verification (+8 more)

### Community 268 - "16. Database model"
Cohesion: 0.33
Nodes (6): 16. Database model, `instruments`, `latest_prices`, `market_ticks`, OHLCV / candles, `provider_instruments`

### Community 272 - "Multi-asset market data"
Cohesion: 0.33
Nodes (6): Current capabilities and limits, Development and validation, Documentation, Multi-asset market data, Quick start, Repository layout

### Community 278 - "Repository layout and existing checkout migration"
Cohesion: 0.33
Nodes (5): Docker Compose and existing data, PyCharm, Repository layout and existing checkout migration, Safe local migration, Why the old layout existed

### Community 279 - "Verified collector / FastAPI Batch 1 integration"
Cohesion: 0.25
Nodes (8): Conflict inventory and resolutions, Future authorized stop-and-replace procedure (not executed), Git scope and strategy, Integrated behavior and schema, Isolated validation, Remaining boundaries / next work, Rollback (not executed on production), Verified collector / FastAPI Batch 1 integration

### Community 280 - "collector/README.md"
Cohesion: 0.33
Nodes (3): Linux collector and worker installation, Windows collector and worker installation, TradingView collector / durable synchronization — v1.1.0rc1 candidate

### Community 281 - "Authorized commercial TradingView preparation"
Cohesion: 0.40
Nodes (5): Authorized commercial TradingView preparation, End-to-end test, Preparation verification — 2026-10-14, Prepared configuration, Target preparation and switch

### Community 282 - "Current state — 2026-10-21"
Cohesion: 0.33
Nodes (5): Current state — 2026-10-21, Implemented, Remaining work, Verified runtime checkpoints, Workspace cleanup

### Community 283 - "30. Testing"
Cohesion: 0.40
Nodes (5): 30. Testing, Persistence integration tests, Provider behaviour tests, Regression tests, Unit tests

### Community 284 - "v11_qualification_source.py"
Cohesion: 0.18
Nodes (3): tracing_store(), write_candles(), write_quotes()

### Community 288 - "Company ingestion protocol v1 (FastAPI v1.1, milestone 2)"
Cohesion: 0.29
Nodes (7): Batch envelope and canonical values, Company ingestion protocol v1 (FastAPI v1.1, milestone 2), Limits and errors, Receipts and retry policy, Routes, Session and ownership fencing, Transport and authentication

### Community 290 - "Collector and FastAPI integration handoff"
Cohesion: 0.40
Nodes (4): Collector and FastAPI integration handoff, Integration points and conflicts, Legacy collector and controlled deployment, Next steps in the third worktree

### Community 292 - "0011_tsetmc_ingestion.py"
Cohesion: 0.60
Nodes (3): downgrade(), streams(), upgrade()

### Community 294 - "13. Timestamp handling"
Cohesion: 0.50
Nodes (4): 13. Timestamp handling, Event timestamp, Persistence timestamp, Received timestamp

### Community 295 - "Implemented execution protocol"
Cohesion: 0.50
Nodes (4): FastAPI v1.1 release preparation, Implemented execution protocol, Live guest pool experiment, Ordinary collector scaling

### Community 296 - "FastAPI v1.1 — milestone 2.1 review"
Cohesion: 0.33
Nodes (6): Actual passing and skipped verification, Database and recovery semantics, FastAPI v1.1 — milestone 2.1 review, Files and rationale, Preservation and remaining operational risks, Recommended milestone 3 design

### Community 331 - "FastAPI v1.1 — milestone 2 review"
Cohesion: 0.40
Nodes (5): Actual verification, FastAPI v1.1 — milestone 2 review, Files and rationale, Migration and transaction design, Preservation and remaining risks

### Community 354 - "M3B-2 disposable CI ownership"
Cohesion: 0.29
Nodes (6): Additional financial review: retained revision adjacency, Final application-code results, M3B-2 disposable CI ownership, Matrix and verification, Two explicit profiles, Windows checkout bytes

### Community 355 - "Simple Ubuntu installation"
Cohesion: 0.12
Nodes (14): ChartData, Dashboard interface, Latest, exact records and corrections, TSETMC validation and source-clock semantics, WebSocket, 1. Install the company API on Ubuntu, 2. Start TradingView, 3. Start TSETMC (+6 more)

### Community 356 - "Simultaneous TradingView collection — 2026-10-14"
Cohesion: 0.29
Nodes (7): Audit and implementation, Deterministic verification, Employer goal verdicts, Registries and genuine source evidence, Safe final qualification and rollout, Semantics and v1.0 compatibility, Simultaneous TradingView collection — 2026-10-14

### Community 357 - "Company ingestion runtime — milestones 2, 2.1 and 3B"
Cohesion: 0.40
Nodes (5): Company ingestion runtime — milestones 2, 2.1 and 3B, Database and private identities, Provision a producer and source ownership, Reproduce only on disposable infrastructure, Start separate read and ingestion processes

### Community 359 - "Completed-development consolidation into main"
Cohesion: 0.40
Nodes (5): Completed-development consolidation into main, Completeness and exclusions, Exact inputs and retained history, Schema and historical compatibility, Validation and production boundary

## Knowledge Gaps
- **4 isolated node(s):** `marketdata-collector-sync`, `marketdata-fastapi`, `marketdata-fastapi`, `marketdata-platform`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 3144 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **125 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `collector()` connect `collector` to `WebSocket market data v1`, `Collector and FastAPI integration handoff`, `v11_qualification_process.py`, `Simultaneous TradingView collection — 2026-10-14`, `asyncio`, `record`, `FastAPI v1.1 integration — Phase A audit and design`, `test_simple_native.py`, `Multi-asset market data`, `InjectedQuotes`, `Experimental TradingView guest market data`, `cursor`, `FastAPI Batch 1: independent processes`, `Verified collector / FastAPI Batch 1 integration`, `WebSocket market data v1`, `v11_qualification_source.py`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **What connects `marketdata-collector-sync`, `marketdata-fastapi`, `marketdata-fastapi` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `benchmark_live_pool.py` be split into smaller, more focused modules?**
  _Cohesion score 0.038580246913580245 - nodes in this community are weakly interconnected._
- **Why does `Quick start` connect `Multi-asset market data` to `collector`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Should `json` be split into smaller, more focused modules?**
  _Cohesion score 0.03049618797650294 - nodes in this community are weakly interconnected._
- **Why does `Multi-asset market data` connect `Multi-asset market data` to `README.md`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Should `src/marketdata/api.py` be split into smaller, more focused modules?**
  _Cohesion score 0.055288461538461536 - nodes in this community are weakly interconnected._