"""Destination gates D01-D05/T05: synthetic state, real PostgreSQL transactions."""

import asyncio
import copy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4, uuid5

import asyncpg
import pytest
from tsetmc_helpers import A, B, imported_rows, tsetmc  # noqa: F401

from marketdata.tsetmc_reconciliation import reconcile
from marketdata.tsetmc_storage import TsetmcWriter
from marketdata.tsetmc_wire import TsetmcError, canonical, digest, financial_hash

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("seed_first", [False, True])
@pytest.mark.parametrize("side", ["old", "new"])
@pytest.mark.parametrize("conflict", [False, True])
async def test_revision_seed_and_full_state_agree_in_both_orders(
    tsetmc,  # noqa: F811
    seed_first,
    side,
    conflict,
):
    t = tsetmc
    seed = t.batch("revision-seed")
    state = t.batch("daily" if side == "old" else "correction")
    record = state["records"][0]
    record["event_type"] = "daily.seed"
    record["observation"]["revision_evidence"] = None
    if conflict:
        record["observation"]["measurements"]["official_close"] = "999"
        rehash(state)
    first, second = (seed, state) if seed_first else (state, seed)
    await commit(t, first)
    before = await imported_rows(t.store)
    if conflict:
        with pytest.raises(TsetmcError, match="source_version_conflict"):
            await commit(t, second)
        assert await imported_rows(t.store) == before
    else:
        await commit(t, second)
        async with t.store.connection() as c:
            assert await c.fetchval("SELECT count(*) FROM company_tsetmc.daily_states") == 1
            assert await c.fetchval("SELECT count(*) FROM company_tsetmc.daily_revisions") == 1
            assert await c.fetchval("SELECT count(*) FROM ingest_observations") == 2
            assert (
                await c.fetchval("SELECT financial_hash FROM company_tsetmc.daily_records")
                == (record["observation"]["financial_hash"])
            )


def quality_state(t, version, position, code=A):
    value = t.batch(position=position, code=code)
    if version == 2:
        r = value["records"][0]
        r["event_type"] = "daily.quality_changed"
        r["observation"]["state_version"] = "2"
        r["observation"]["reconciliation"].update(
            status="unresolved_conflict", open_quarantine_count=1
        )
    return value


@pytest.mark.parametrize(
    "sequence,reject",
    [
        ([(1, 1), (1, 10), (2, 5)], True),
        ([(1, 1), (2, 5), (1, 10)], True),
        ([(1, 4), (2, 5), (2, 3)], True),
        ([(2, 5), (2, 10), (1, 7)], True),
        ([(1, 10), (2, 11), (1, 1)], False),
        ([(2, 5), (1, 1), (1, 4)], False),
        ([(1, 1), (1, 4), (2, 5)], False),
        ([(1, 4), (2, 5), (1, 1)], False),
    ],
)
async def test_daily_alias_ordering_uses_every_retained_position(tsetmc, sequence, reject):  # noqa: F811
    t = tsetmc
    for version, position in sequence[:2]:
        await commit(t, quality_state(t, version, position))
    before = await imported_rows(t.store)
    last = quality_state(t, *sequence[2])
    if reject:
        with pytest.raises(TsetmcError, match="source_version_conflict"):
            await commit(t, last)
        assert await imported_rows(t.store) == before
    else:
        receipt = await commit(t, last)
        assert await commit(t, last) == receipt
        duplicate = copy.deepcopy(last)
        duplicate["batch_id"] = str(uuid4())
        assert (await commit(t, duplicate))["records"][0]["outcome"] == "duplicate"
        async with t.store.connection() as c:
            assert await c.fetchval("SELECT state_version FROM company_tsetmc.daily_records") == 2


async def test_alias_barriers_do_not_cross_instrument_epochs(tsetmc):  # noqa: F811
    t = tsetmc
    for code in (A, B):
        await commit(t, quality_state(t, 1, 1, code))
    await commit(t, quality_state(t, 1, 10, A))
    assert (await commit(t, quality_state(t, 2, 5, B)))["records"][0]["canonical_updated"]
    before = await imported_rows(t.store)
    with pytest.raises(TsetmcError, match="source_version_conflict"):
        await commit(t, quality_state(t, 2, 5, A))
    assert await imported_rows(t.store) == before


async def test_quarantine_quality_and_reconciliation_keep_accepted_financial_state(tsetmc):  # noqa: F811
    t = tsetmc
    original = t.batch()
    await commit(t, original)
    for position, event, acceptance, status, count in (
        (2, "daily.quality_changed", "observed", "unresolved_conflict", 1),
        (3, "daily.reconciled", "reconciled", "agrees", 0),
    ):
        value = t.batch(position=position)
        record = value["records"][0]
        record["event_type"] = event
        observation = record["observation"]
        observation.update(state_version=str(position), acceptance=acceptance)
        observation["reconciliation"].update(
            status=status, local_decision_id=str(position), open_quarantine_count=count
        )
        await commit(t, value)
        async with t.store.connection() as c:
            head = await c.fetchrow("SELECT * FROM company_tsetmc.daily_records")
            assert head["financial_hash"] == original["records"][0]["observation"]["financial_hash"]
            assert head["financial_revision"] == 1 and head["state_version"] == position
            assert head["upstream_finality"] == "unverified"
            assert (
                await c.fetchval("SELECT kind FROM company_tsetmc.events ORDER BY id DESC LIMIT 1")
                == event
            )


@pytest.mark.parametrize("fence", ["owner", "epoch", "generation", "key", "disabled"])
async def test_administrative_fences_do_not_rewrite_imports(tsetmc, fence):  # noqa: F811
    t = tsetmc
    value = t.batch()
    await commit(t, value)
    async with t.store.connection() as c:
        if fence == "owner":
            replacement = uuid4()
            await c.execute(
                "INSERT INTO ingest_producers(producer_id,label,credential_key_id,"
                "session_id,session_generation,session_expires_at) "
                "VALUES($1,'synthetic replacement','synthetic_replacement',"
                "gen_random_uuid(),1,clock_timestamp()+interval '120 seconds')",
                replacement,
            )
            await c.execute(
                "UPDATE ingest_source_owners SET producer_id=$1,ownership_generation=2", replacement
            )
        else:
            await c.execute(
                {
                    "epoch": (
                        "UPDATE ingest_source_owners SET source_epoch=gen_random_uuid(),"
                        "ownership_generation=2"
                    ),
                    "generation": "UPDATE ingest_source_owners SET ownership_generation=2",
                    "key": "UPDATE ingest_producers SET credential_key_id='synthetic_rotated'",
                    "disabled": "UPDATE ingest_producers SET enabled=FALSE",
                }[fence]
            )
    with pytest.raises(TsetmcError):
        await commit(t, value)
    async with t.store.connection() as c:
        assert await c.fetchval("SELECT count(*) FROM ingest_batches") == 1
        assert await c.fetchval("SELECT count(*) FROM company_tsetmc.events") == 1


async def test_producer_first_lock_serializes_revocation_behind_commit(tsetmc):  # noqa: F811
    t = tsetmc
    entered, release = asyncio.Event(), asyncio.Event()

    async def pause(boundary):
        if boundary == "before_commit":
            entered.set()
            await release.wait()

    async def revoke():
        async with t.store.connection() as c, c.transaction():
            await c.fetchrow(
                "SELECT * FROM ingest_producers WHERE producer_id=$1 FOR UPDATE", t.producer
            )
            await c.execute(
                "UPDATE ingest_producers SET enabled=FALSE WHERE producer_id=$1", t.producer
            )

    t.writer.checkpoint = pause
    upload = asyncio.create_task(commit(t, t.batch()))
    await asyncio.wait_for(entered.wait(), 5)
    revoker = asyncio.create_task(revoke())
    try:
        await asyncio.sleep(0.1)
        assert not revoker.done()
        release.set()
        assert (await upload)["state"] == "committed"
        await revoker
        with pytest.raises(TsetmcError, match="producer_not_authorized"):
            await commit(t, t.batch(position=2))
    finally:
        release.set()
        await asyncio.gather(upload, revoker, return_exceptions=True)


async def test_database_context_fk_and_revision_numeric_constraints(tsetmc):  # noqa: F811
    t = tsetmc
    await commit(t, t.batch())
    async with t.store.connection() as c:
        with pytest.raises(asyncpg.ForeignKeyViolationError):
            async with c.transaction():
                await c.execute("SET CONSTRAINTS ALL IMMEDIATE")
                await c.execute("UPDATE company_tsetmc.daily_records SET source_position=999")
    await commit(t, t.batch("correction"))
    async with t.store.connection() as c:
        evidence = dict(await c.fetchrow("SELECT * FROM company_tsetmc.daily_revisions"))
        evidence["financial_revision"] = 3
        for invalid in (Decimal("-1"), Decimal("NaN"), Decimal("Infinity"), Decimal("0.5")):
            evidence["old_trade_count"] = invalid
            with pytest.raises(asyncpg.CheckViolationError):
                async with c.transaction():
                    await c.execute(
                        "INSERT INTO company_tsetmc.daily_revisions ("
                        + ",".join(evidence)
                        + ") VALUES ("
                        + ",".join(f"${i}" for i in range(1, len(evidence) + 1))
                        + ")",
                        *evidence.values(),
                    )


async def test_equal_state_redelivery_preserves_historical_fence(tsetmc):  # noqa: F811
    t = tsetmc
    # Import the same approved public state at position 2 before position 1.
    await commit(t, t.batch(position=2))
    await commit(t, t.batch(position=1))
    result = await reconcile(t.writer, t.principal, request(t, fence="1"))
    assert result["rows"][0]["source_position"] == "1"
    assert result["rows"][0]["state_version"] == "1"
    latest = await reconcile(t.writer, t.principal, request(t, fence="2"))
    assert latest["rows"][0]["source_position"] == "2"
    async with t.store.connection() as c:
        assert await c.fetchval("SELECT count(*) FROM company_tsetmc.daily_states") == 1
        assert await c.fetchval("SELECT count(*) FROM ingest_observations") == 2


async def test_revision_seed_cannot_contradict_retained_accepted_state(tsetmc):  # noqa: F811
    t = tsetmc
    await commit(t, t.batch())
    value = t.batch("revision-seed")
    observation = value["records"][0]["observation"]
    evidence = observation["revision_evidence"]
    evidence["old_measurements"]["official_close"] = "999"
    evidence["old_financial_hash"] = financial_hash(observation, evidence["old_measurements"])
    with pytest.raises(TsetmcError, match="source_version_conflict"):
        await commit(t, value)


async def test_status_fractional_clock_ordering_and_nested_future_evidence(tsetmc):  # noqa: F811
    t = tsetmc
    instant = datetime.now(UTC).replace(microsecond=0) - timedelta(seconds=1)
    first = t.batch("status", position=1)
    first["records"][0]["observation"].update(
        captured_at=instant.isoformat().replace("+00:00", "Z"),
        expires_at=(instant + timedelta(seconds=60)).isoformat().replace("+00:00", "Z"),
    )
    await commit(t, first)
    second = copy.deepcopy(first)
    second["batch_id"] = str(uuid4())
    second["records"][0].update(
        source_position="2", observation_id=str(uuid5(t.epochs[A], "tsetmc_status:2"))
    )
    second["records"][0]["observation"]["captured_at"] = (
        (instant + timedelta(microseconds=1)).isoformat().replace("+00:00", "Z")
    )
    assert (await commit(t, second))["records"][0]["outcome"] == "recorded_no_change"
    confirmation = t.batch("confirmation")
    confirmation["records"][0]["observation"]["review"]["reviewed_at"] = (
        (datetime.now(UTC) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
    )
    with pytest.raises(TsetmcError, match="collector_clock_ahead"):
        await commit(t, confirmation)


async def test_reconciliation_huge_revision_is_bounded_and_incomplete(tsetmc):  # noqa: F811
    t = tsetmc
    value = t.batch("correction", position=1)
    observation = value["records"][0]["observation"]
    observation["financial_revision"] = str(2**63 - 2)
    observation["revision_evidence"]["financial_revision"] = observation["financial_revision"]
    await commit(t, value)
    result = await reconcile(t.writer, t.principal, request(t, fence="1"))
    assert result["rows"][0]["revision_count"] == 1
    assert result["rows"][0]["revision_complete"] is False


async def commit(t, value):
    return await t.writer.commit(t.principal, canonical(value))


def rehash(value):
    for record in value["records"]:
        o = record["observation"]
        o["financial_hash"] = financial_hash(o)
        if o.get("review"):
            o["review"]["reviewed_financial_hash"] = o["financial_hash"]
    return value


def current(t, position, seconds=0, **changes):
    value = t.batch("current", position=position)
    o = value["records"][0]["observation"]
    instant = datetime.fromisoformat(o["source_reported_at"]) + timedelta(seconds=seconds)
    o["source_reported_at"] = instant.isoformat().replace("+00:00", "Z")
    o["source_time"] = (instant + timedelta(hours=3, minutes=30)).strftime("%H:%M:%S")
    o.update(changes)
    return rehash(value)


def request(t, *, code=A, mode="daily_manifest", fence="4", **changes):
    value = dict(
        protocol_version=1,
        contract_version="tsetmc.v1",
        session_id=str(t.session),
        session_generation=1,
        instrument_id=str(t.identity(code)),
        ins_code=code,
        source_epoch=str(t.epochs[code]),
        ownership_generation=1,
        mode=mode,
    )
    if mode == "daily_manifest":
        value.update(
            source_fence=fence,
            from_date="2026-03-01",
            through_date="2026-03-31",
            after_date=None,
            limit=100,
        )
    else:
        value["keys"] = [dict(stream="tsetmc_daily", trading_date="2026-03-21")]
    value.update(changes)
    return value


async def test_daily_lifecycle_exact_receipts_and_reconciliation(tsetmc):  # noqa: F811
    t = tsetmc
    for name in ("daily", "confirmation", "revocation", "correction", "revision-seed"):
        value = t.batch(name)
        receipt = await commit(t, value)
        assert await commit(t, value) == receipt
        assert receipt["records"][0]["stored_state_version"] == value["records"][0][
            "observation"
        ].get("state_version")
    async with t.store.connection() as c:
        row = await c.fetchrow("SELECT * FROM company_tsetmc.daily_records")
        assert row["official_close"] == Decimal("113") and row["high"] == Decimal("110")
        assert row["financial_revision"] == 2 and row["state_version"] == 4
        assert row["local_finalization"] == "source_unverified"
        assert await c.fetchval("SELECT count(*) FROM company_tsetmc.daily_states") == 4
        assert await c.fetchval("SELECT count(*) FROM company_tsetmc.daily_revisions") == 1
        assert await c.fetchval("SELECT count(*) FROM ingest_observations") == 5
        assert await c.fetchval("SELECT count(*) FROM company_tsetmc.events") == 4
        assert await c.fetchval("SELECT count(*) FROM marketdata_events") == 0
        assert await c.fetchval("SELECT head FROM marketdata_event_clock") == t.legacy_head
    result = await reconcile(t.writer, t.principal, request(t))
    state = t.batch("correction")["records"][0]["observation"]
    assert result["rows"][0]["state_sha256"] == digest(state)
    assert result["rows"][0]["revision_sha256"] == digest([state["revision_evidence"]])
    assert result["rows"][0]["revision_complete"] is True
    assert result["page_sha256"] == digest(result["rows"])


async def test_reverse_delivery_retains_superseded_state_and_source_ack_fields(tsetmc):  # noqa: F811
    t = tsetmc
    await commit(t, t.batch("correction"))
    for name in ("revocation", "confirmation", "daily"):
        value = t.batch(name)
        receipt = await commit(t, value)
        assert receipt["records"][0]["outcome"] == "superseded"
        assert receipt["records"][0]["canonical_updated"] is False
        assert (
            receipt["records"][0]["stored_state_version"]
            == value["records"][0]["observation"]["state_version"]
        )
    async with t.store.connection() as c:
        assert await c.fetchval("SELECT state_version FROM company_tsetmc.daily_records") == 4
        assert await c.fetchval("SELECT count(*) FROM company_tsetmc.daily_states") == 4
        assert await c.fetchval("SELECT count(*) FROM company_tsetmc.events") == 1
    result = await reconcile(t.writer, t.principal, request(t, fence="2"))
    assert result["rows"][0]["state_version"] == "2"


async def test_two_instruments_independent_epochs_positions_and_registry_isolation(tsetmc):  # noqa: F811
    t = tsetmc
    await commit(t, t.batch(code=A))
    await commit(t, t.batch(code=B))
    assert t.epochs[A] != t.epochs[B]
    async with t.store.connection() as c:
        assert await c.fetchval("SELECT count(*) FROM company_tsetmc.daily_records") == 2
        assert await c.fetchval("SELECT count(DISTINCT source_epoch) FROM ingest_observations") == 2
    registry = await t.store.registry()
    assert all(not s.startswith("TSETMC:") for s in registry.by_symbol)
    assert await t.store.instrument("TSETMC:" + A) is None
    assert await t.store.known_symbols(["TSETMC:" + A]) == set()
    assert all(
        not r["canonical_symbol"].startswith("TSETMC:") for r in await t.store.instruments(100)
    )
    assert all(
        r["provider"] != "tsetmc" for r in await t.store.source_records(None, None, None, None, 100)
    )


async def test_precision_nulls_and_zero(tsetmc):  # noqa: F811
    t = tsetmc
    value = t.batch()
    o = value["records"][0]["observation"]
    o["measurements"].update(
        previous_close="100.123456789012345678901234567890123456789",
        trade_count="9" * 128,
        traded_volume="0",
        traded_value=None,
    )
    rehash(value)
    await commit(t, value)
    async with t.store.connection() as c:
        row = await c.fetchrow(
            """SELECT previous_close,trade_count,traded_volume,traded_value
            FROM company_tsetmc.daily_records"""
        )
        assert row["previous_close"] == Decimal(o["measurements"]["previous_close"])
        assert row["trade_count"] == Decimal("9" * 128)
        assert row["traded_volume"] == 0 and row["traded_value"] is None


async def test_one_invalid_record_rolls_back_data_journal_ledger_receipt(tsetmc):  # noqa: F811
    t = tsetmc
    value = t.batch()
    second = copy.deepcopy(value["records"][0])
    second["source_position"] = "2"
    second["observation_id"] = str(uuid5(t.epochs[A], "tsetmc_daily:2"))
    second["observation"]["trading_date"] = "2026-03-22"
    second["observation"]["source_instrument_id"] = "UNAPPROVED-SYNTHETIC-BINDING"
    value["records"].append(second)
    rehash(value)
    async with t.store.connection() as c:
        head = await c.fetchval("SELECT head FROM company_tsetmc.event_clock")
    with pytest.raises(TsetmcError) as caught:
        await commit(t, value)
    assert caught.value.indexes == [1]
    async with t.store.connection() as c:
        for table in ("daily_records", "daily_states", "events"):
            assert await c.fetchval(f"SELECT count(*) FROM company_tsetmc.{table}") == 0
        assert await c.fetchval("SELECT count(*) FROM ingest_batches") == 0
        assert await c.fetchval("SELECT count(*) FROM ingest_observations") == 0
        assert await c.fetchval("SELECT head FROM company_tsetmc.event_clock") == head


@pytest.mark.parametrize("mode", ["bytes", "observation", "version", "epoch", "ownership"])
async def test_conflicting_retries_fail_closed(tsetmc, mode):  # noqa: F811
    t = tsetmc
    value = t.batch()
    await commit(t, value)
    if mode == "bytes":
        with pytest.raises(TsetmcError, match="batch_payload_conflict"):
            await t.writer.commit(t.principal, canonical(value) + b"\n")
        return
    value["batch_id"] = str(uuid4())
    if mode in {"observation", "version"}:
        value["records"][0]["observation"]["publication_state"] = "provisional"
        if mode == "version":
            record = value["records"][0]
            record["source_position"] = "2"
            record["observation_id"] = str(uuid5(t.epochs[A], "tsetmc_daily:2"))
    elif mode == "epoch":
        value["source_epoch"] = str(uuid4())
        value["records"][0]["observation_id"] = str(
            uuid5(UUID(value["source_epoch"]), "tsetmc_daily:1")
        )
    else:
        value["ownership_generation"] = 2
    with pytest.raises(TsetmcError):
        await commit(t, value)


async def test_current_coalesced_local_false_updates_company_and_clock_guards(tsetmc):  # noqa: F811
    t = tsetmc
    await commit(t, current(t, 1))
    value = current(t, 3, 2, financial_change=False)
    value["records"][0]["observation"]["measurements"]["official_close"] = "112"
    rehash(value)
    await commit(t, value)
    async with t.store.connection() as c:
        assert await c.fetchval("SELECT official_close FROM company_tsetmc.current_latest") == 112
        assert (
            await c.fetchval(
                "SELECT measurements_changed FROM company_tsetmc.events ORDER BY id DESC LIMIT 1"
            )
            is True
        )
    older = current(t, 4, 1)
    with pytest.raises(TsetmcError, match="current_source_regression"):
        await commit(t, older)
    ambiguous = current(t, 4, 2)
    with pytest.raises(TsetmcError, match="current_source_regression"):
        await commit(t, ambiguous)
    ambiguous["records"][0]["observation"].update(
        accepted_decision="explicit_same_time_correction",
        correction_reason_sha256=digest("synthetic decision"),
    )
    await commit(t, ambiguous)
    position = current(t, 5, 3, financial_change=False)
    await commit(t, position)
    async with t.store.connection() as c:
        assert (
            await c.fetchval("SELECT kind FROM company_tsetmc.events ORDER BY id DESC LIMIT 1")
            == "current.position_updated"
        )


async def test_coverage_pages_do_not_delete_omitted_dates_and_status_does_not_refresh(tsetmc):  # noqa: F811
    t = tsetmc
    coverage = t.batch("coverage")
    await commit(t, coverage)
    coverage2 = t.batch("coverage", position=2)
    page = coverage2["records"][0]["observation"]
    page.update(from_date="2026-03-22", through_date="2026-03-22")
    page["coverage_rows"][0]["trading_date"] = "2026-03-22"
    await commit(t, coverage2)
    status = t.batch("status")
    now = datetime.now(UTC)
    o = status["records"][0]["observation"]
    o.update(
        captured_at=now.isoformat().replace("+00:00", "Z"),
        expires_at=(now + timedelta(seconds=60)).isoformat().replace("+00:00", "Z"),
    )
    await commit(t, status)
    heartbeat = t.batch("status", position=2)
    heartbeat["records"][0]["observation"] = copy.deepcopy(o)
    receipt = await commit(t, heartbeat)
    assert receipt["records"][0]["outcome"] == "recorded_no_change"
    expired = t.batch("status", position=3)
    assert (await commit(t, expired))["records"][0]["outcome"] == "recorded_no_change"
    async with t.store.connection() as c:
        assert await c.fetchval("SELECT count(*) FROM company_tsetmc.daily_coverage") == 2
        row = await c.fetchrow("SELECT * FROM company_tsetmc.source_status")
        assert row["source_position"] == 2 and row["expires_at"] == now + timedelta(seconds=60)
        assert (
            await c.fetchval(
                "SELECT count(*) FROM company_tsetmc.events WHERE kind='status.updated'"
            )
            == 1
        )


async def test_reconciliation_pages_at_fence_and_missing_prefix(tsetmc):  # noqa: F811
    t = tsetmc
    await commit(t, t.batch())
    second = t.batch(position=2)
    second["records"][0]["observation"]["trading_date"] = "2026-03-22"
    rehash(second)
    await commit(t, second)
    first = await reconcile(t.writer, t.principal, request(t, fence="2", limit=1))
    assert first["has_more"] and first["next_after_date"] == "2026-03-21"
    confirmation = t.batch("confirmation", position=3)
    await commit(t, confirmation)
    page2 = await reconcile(
        t.writer, t.principal, request(t, fence="2", limit=1, after_date=first["next_after_date"])
    )
    assert not page2["has_more"] and page2["rows"][0]["trading_date"] == "2026-03-22"
    old = await reconcile(t.writer, t.principal, request(t, fence="2"))
    assert old["rows"][0]["state_version"] == "1"
    await commit(t, t.batch(code=B, position=2))
    with pytest.raises(TsetmcError, match="reconciliation_history_unavailable"):
        await reconcile(t.writer, t.principal, request(t, code=B, fence="2"))


@pytest.mark.parametrize("rollback", [False, True])
async def test_concurrent_journal_commit_order_and_rollback_no_precommit_visibility(
    tsetmc,  # noqa: F811
    rollback,
):
    t = tsetmc
    entered, release = asyncio.Event(), asyncio.Event()

    async def pause(boundary):
        if boundary == "before_commit":
            entered.set()
            await release.wait()
            if rollback:
                raise RuntimeError("synthetic transaction failure")

    t.writer.checkpoint = pause
    async with t.store.connection() as c:
        old_head = await c.fetchval("SELECT head FROM company_tsetmc.event_clock")
    first = asyncio.create_task(commit(t, t.batch()))
    await asyncio.wait_for(entered.wait(), 5)
    writer2 = TsetmcWriter(t.store)
    second = asyncio.create_task(writer2.commit(t.principal, canonical(t.batch(code=B))))
    try:
        await asyncio.sleep(0.1)
        assert not second.done()
        async with t.store.connection() as c:
            assert await c.fetchval("SELECT count(*) FROM company_tsetmc.events") == 0
        release.set()
        if rollback:
            with pytest.raises(RuntimeError):
                await first
        else:
            await first
        await second
        async with t.store.connection() as c:
            ids = [
                r["id"] for r in await c.fetch("SELECT id FROM company_tsetmc.events ORDER BY id")
            ]
            assert ids == list(range(old_head + 1, old_head + (2 if rollback else 3)))
            assert await c.fetchval("SELECT head FROM marketdata_event_clock") == t.legacy_head
    finally:
        release.set()
        await asyncio.gather(first, second, return_exceptions=True)


@pytest.mark.parametrize("boundary", ["before_receipt", "before_commit", "after_commit"])
async def test_response_loss_and_transaction_failure_replay(tsetmc, boundary):  # noqa: F811
    t = tsetmc
    value = t.batch()

    async def fail(point):
        if point == boundary:
            raise ConnectionError("synthetic response loss")

    t.writer.checkpoint = fail
    with pytest.raises(ConnectionError):
        await commit(t, value)
    t.writer = TsetmcWriter(t.store)
    receipt = await commit(t, value)
    assert receipt["state"] == "committed"
    async with t.store.connection() as c:
        assert await c.fetchval("SELECT count(*) FROM ingest_batches") == 1
        assert await c.fetchval("SELECT count(*) FROM company_tsetmc.events") == 1
