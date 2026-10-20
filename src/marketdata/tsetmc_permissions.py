"""Namespace permissions, separate from unchanged legacy writer requirements."""

from typing import Any

TABLES = (
    "instrument_links",
    "daily_records",
    "daily_states",
    "daily_revisions",
    "current_latest",
    "daily_coverage",
    "source_status",
    "event_clock",
    "events",
)


async def privilege(c: Any, table: str, permissions: str) -> bool:
    # OID lookup avoids requiring USAGE on the namespace being inspected.
    return bool(
        await c.fetchval(
            """SELECT has_table_privilege(current_user,t.oid,$2)
        FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace
        WHERE n.nspname=split_part($1,'.',1) AND t.relname=split_part($1,'.',2)""",
            table,
            permissions,
        )
    )


async def validate_permissions(c: Any, *, read_only: bool) -> None:
    unsafe = await c.fetchval("SELECT has_schema_privilege(current_user,'company_tsetmc','CREATE')")
    for table in TABLES:
        name = "company_tsetmc." + table
        forbidden = (
            "INSERT,UPDATE,DELETE,TRUNCATE"
            if read_only
            else (
                "INSERT,UPDATE,DELETE,TRUNCATE"
                if table == "instrument_links"
                else "UPDATE,DELETE,TRUNCATE"
                if table in {"daily_states", "daily_revisions", "events"}
                else "DELETE,TRUNCATE"
            )
        )
        unsafe = unsafe or await privilege(c, name, forbidden)
        if not read_only:
            required = ["SELECT"]
            if table != "instrument_links":
                required.append("UPDATE" if table == "event_clock" else "INSERT")
            if table in {"daily_records", "current_latest", "daily_coverage", "source_status"}:
                required.append("UPDATE")
            for permission in required:
                if not await privilege(c, name, permission):
                    raise RuntimeError("restricted TSETMC writer permissions required")
    prune = await c.fetchval(
        "SELECT has_function_privilege(current_user,p.oid,'EXECUTE') "
        "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
        "WHERE n.nspname='company_tsetmc' AND p.proname='prune_events' "
        "AND p.proargtypes='23'::oidvector"
    )
    binding_lock = await c.fetchval(
        "SELECT has_function_privilege(current_user,p.oid,'EXECUTE') "
        "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
        "WHERE n.nspname='company_tsetmc' AND p.proname='lock_instrument' "
        "AND p.proargtypes='2950'::oidvector"
    )
    if read_only:
        unsafe = unsafe or prune or binding_lock
        for table in (
            "ingest_producers",
            "ingest_source_owners",
            "ingest_batches",
            "ingest_observations",
            "ingest_session_recoveries",
            "ingest_request_budgets",
        ):
            unsafe = unsafe or await privilege(c, "public." + table, "SELECT")
    elif not prune:
        raise RuntimeError("restricted TSETMC retention permission required")
    elif not binding_lock:
        raise RuntimeError("restricted TSETMC binding lock permission required")
    if unsafe:
        raise RuntimeError("unsafe TSETMC runtime permissions")
