"""End-to-end smoke test for ``POST /entities/ensure`` against a LIVE API.

Fires many concurrent ensure calls with the *same* match query through the full
HTTP stack and asserts exactly one entity is created — exercising request
parsing, routing, the SERIALIZABLE retry loop, and convergence end-to-end.

NOTE: the find-then-create window is microseconds, so the first inserter usually
commits before the others read and the race seldom actually fires here — a green
run is necessary but not sufficient. The *deterministic* atomicity proof (SSI
aborts the second committer with 40001, vs. READ COMMITTED duplicating) lives in
``test_ensure_atomicity_db.py``, which interleaves two transactions by hand.

Skipped unless ``DATA_API_LIVE_URL`` points at a running API backed by real
Postgres, e.g.::

    DATA_API_LIVE_URL=http://localhost:8080/v1 python -m pytest \\
        tests/test_ensure_atomicity_live.py -q
"""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import httpx
import pytest

LIVE_URL = os.environ.get("DATA_API_LIVE_URL")

pytestmark = pytest.mark.skipif(
    not LIVE_URL, reason="set DATA_API_LIVE_URL to run the live atomicity test"
)

_CONCURRENCY = 24


def _ensure_payload(dataset_name: str, project_id: str) -> dict:
    where = {
        "type": "group",
        "op": "and",
        "children": [
            {
                "type": "filter",
                "field": "metadata.dataset.name",
                "op": "eq",
                "value": dataset_name,
            },
            {
                "type": "filter",
                "field": "metadata.permissions.project",
                "op": "eq",
                "value": project_id,
            },
        ],
    }
    return {
        "where": where,
        "entity": {
            "id": str(uuid4()),  # fresh per call; loser's id is discarded
            "storage_coordinates": [],
            "metadata": [
                {"key": "dataset", "data": {"name": dataset_name}, "artifacts": []},
                {
                    "key": "permissions",
                    "data": {"project": project_id, "owner": None},
                    "artifacts": [],
                },
            ],
        },
    }


@pytest.mark.asyncio
async def test_concurrent_ensure_creates_exactly_one() -> None:
    dataset_name = f"race-{uuid4()}"
    project_id = str(uuid4())

    async with httpx.AsyncClient(base_url=LIVE_URL, timeout=30.0) as client:

        async def call() -> dict:
            resp = await client.post(
                "/entities/ensure", json=_ensure_payload(dataset_name, project_id)
            )
            resp.raise_for_status()
            return resp.json()

        results = await asyncio.gather(*(call() for _ in range(_CONCURRENCY)))

        # Exactly one inserter; everyone converges on one entity id.
        created_count = sum(1 for r in results if r["created"])
        ids = {r["entity"]["id"] for r in results}
        assert created_count == 1, f"expected 1 create, got {created_count}"
        assert len(ids) == 1, f"converged on >1 entity: {ids}"

        # The database really holds a single matching row.
        where = _ensure_payload(dataset_name, project_id)["where"]
        q = await client.post("/entities/query", json={"where": where, "limit": 100})
        q.raise_for_status()
        assert q.json()["total_count"] == 1

        # A follow-up ensure is a pure read: no new entity, returns the same id.
        again = await call()
        assert again["created"] is False
        assert again["entity"]["id"] == next(iter(ids))
