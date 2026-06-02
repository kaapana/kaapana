"""Deterministic proof that ``POST /entities/ensure`` is atomic — at the DB level.

The HTTP smoke test (``test_ensure_atomicity_live``) fires many concurrent ensure
calls, but the find-then-create window is microseconds, so the first inserter
usually commits before the others read — the race rarely fires and a green run is
weak evidence. This test instead **interleaves two transactions by hand** through
the exact code path the endpoint uses (``execute_entity_query`` for the "no match"
read, then an insert), and asserts the property the endpoint's retry loop depends
on: under SERIALIZABLE, Postgres SSI aborts the second committer with
serialization_failure (SQLSTATE 40001), leaving exactly one row. A sibling
assertion shows READ COMMITTED would instead let both commit (two rows) — the
duplicate-dataset bug this endpoint exists to prevent.

Skipped unless ``DATA_API_TEST_DATABASE_URL`` points at a throwaway Postgres with
the migrations applied, e.g.::

    DATA_API_TEST_DATABASE_URL=postgresql://kaapanauser:kaapanapassword@localhost:5433/kaapanauser \\
        python -m pytest tests/test_ensure_atomicity_db.py -q
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.domain import DataEntity
from app.models.query import QueryRequest
from app.services.entity_query import execute_entity_query
from app.services.entity_repository import entity_to_orm

DB_URL = os.environ.get("DATA_API_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DB_URL,
    reason="set DATA_API_TEST_DATABASE_URL (migrated Postgres) to run the SSI test",
)


def _where(name: str, project: str) -> dict:
    return {
        "type": "group",
        "op": "and",
        "children": [
            {
                "type": "filter",
                "field": "metadata.dataset.name",
                "op": "eq",
                "value": name,
            },
            {
                "type": "filter",
                "field": "metadata.permissions.project",
                "op": "eq",
                "value": project,
            },
        ],
    }


def _entity(name: str, project: str) -> DataEntity:
    return DataEntity.model_validate(
        {
            "id": str(uuid4()),
            "storage_coordinates": [],
            "metadata": [
                {"key": "dataset", "data": {"name": name}, "artifacts": []},
                {
                    "key": "permissions",
                    "data": {"project": project, "owner": None},
                    "artifacts": [],
                },
            ],
        }
    )


async def _interleave(isolation: str) -> tuple[bool, str | None, int]:
    """Run the two-transaction ensure race at ``isolation``.

    Returns ``(second_committed, second_sqlstate, matching_rows)``.
    """
    engine = create_async_engine(
        DB_URL.replace("postgresql://", "postgresql+asyncpg://")
    )
    session_factory = async_sessionmaker(
        bind=engine, expire_on_commit=False, autoflush=False
    )
    name, project = f"ssi-{uuid4()}", str(uuid4())
    where = _where(name, project)
    query = QueryRequest(where=where, limit=1)

    s1, s2 = session_factory(), session_factory()
    try:
        for session in (s1, s2):
            await session.connection(execution_options={"isolation_level": isolation})
        # Both observe "no match" — under SERIALIZABLE this predicate-locks the read.
        m1, _, _ = await execute_entity_query(s1, query)
        m2, _, _ = await execute_entity_query(s2, query)
        assert not m1 and not m2, "precondition: nothing matches yet"

        s1.add(entity_to_orm(_entity(name, project)))
        s2.add(entity_to_orm(_entity(name, project)))

        await s1.commit()  # winner
        second_committed, second_sqlstate = True, None
        try:
            await s2.commit()
        except DBAPIError as exc:
            await s2.rollback()
            second_committed = False
            second_sqlstate = getattr(exc.orig, "sqlstate", None)

        async with session_factory() as s3:
            rows, _, _ = await execute_entity_query(
                s3, QueryRequest(where=where, limit=10)
            )
        return second_committed, second_sqlstate, len(rows)
    finally:
        await s1.close()
        await s2.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_serializable_aborts_the_second_creator() -> None:
    """SSI must abort the loser with 40001, leaving exactly one row.

    This is the exact condition ``entities._is_serialization_failure`` detects and
    the ensure retry loop relies on to converge to a single entity.
    """
    committed, sqlstate, rows = await _interleave("SERIALIZABLE")
    assert committed is False, "SERIALIZABLE let both creators commit — not atomic"
    assert sqlstate == "40001", f"expected serialization_failure, got {sqlstate}"
    assert rows == 1


@pytest.mark.asyncio
async def test_read_committed_would_duplicate() -> None:
    """Negative control: without SSI the race produces two rows (the bug)."""
    committed, _sqlstate, rows = await _interleave("READ COMMITTED")
    assert committed is True
    assert rows == 2
