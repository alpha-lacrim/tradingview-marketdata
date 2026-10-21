"""Additional schema permission checks for the optional company extension."""

from typing import Any


async def validate_permissions(c: Any, *, read_only: bool) -> None:
    for name in ("heads", "events", "clock"):
        table = "company_tsetmc." + name
        if not await c.fetchval("SELECT has_table_privilege(current_user,$1,'SELECT')", table):
            raise RuntimeError("TSETMC role lacks required read privileges")
        forbidden = "INSERT,UPDATE,DELETE,TRUNCATE" if read_only else "DELETE,TRUNCATE"
        if not read_only and name == "events":
            forbidden += ",UPDATE"
        if not read_only and name == "clock":
            forbidden += ",INSERT"
        if await c.fetchval("SELECT has_table_privilege(current_user,$1,$2)", table, forbidden):
            raise RuntimeError("TSETMC role has unsafe mutation privileges")
        if not read_only:
            for privilege in (
                ["INSERT"]
                if name == "events"
                else ["UPDATE"]
                if name == "clock"
                else ["INSERT", "UPDATE"]
            ):
                if not await c.fetchval(
                    "SELECT has_table_privilege(current_user,$1,$2)", table, privilege
                ):
                    raise RuntimeError("TSETMC writer lacks required mutation privileges")
    if await c.fetchval("SELECT has_schema_privilege(current_user,'company_tsetmc','CREATE')"):
        raise RuntimeError("TSETMC runtime must not own its schema")
