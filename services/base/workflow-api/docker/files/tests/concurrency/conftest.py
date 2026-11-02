# ruff: noqa: E402
"""
Fixtures for the concurrency tests.

SQLite ignores row locks, so these tests need a PostgreSQL database. They run
only if WORKFLOW_API_TEST_DATABASE_URL is set, for example:

    docker run -d --rm --name wfapi-pg -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test \\
        -e POSTGRES_DB=wfapi -p 127.0.0.1:5433:5432 postgres:18-alpine
    WORKFLOW_API_TEST_DATABASE_URL=postgresql+asyncpg://test:test@127.0.0.1:5433/wfapi pytest tests/concurrency
"""

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import JSON
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
postgresql.JSONB = JSON
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import crud, models, schemas
from app.adapters.adapters.dummy_adapter import DummyAdapter
from app.api.v1.services import workflow_run_service as service
from app.models import Base

DATABASE_URL = os.environ.get("WORKFLOW_API_TEST_DATABASE_URL")


def pytest_collection_modifyitems(config, items):
    if DATABASE_URL:
        return
    skip = pytest.mark.skip(reason="WORKFLOW_API_TEST_DATABASE_URL is not set")
    for item in items:
        if "tests/concurrency" in str(item.fspath):
            item.add_marker(skip)


@pytest_asyncio.fixture
async def session_factory(monkeypatch):
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _own_session():
        async with factory() as s:
            yield s

    monkeypatch.setattr(service, "get_async_db", _own_session)
    DummyAdapter.reset_cleanup_state()

    yield factory

    DummyAdapter.reset_cleanup_state()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def make_run(session_factory):
    async def _make(
        lifecycle: schemas.WorkflowRunStatus,
        external_id: str | None = "dummy::run-1",
    ) -> int:
        async with session_factory() as s:
            workflow = models.Workflow(title="locking-wf", workflow_engine="dummy")
            s.add(workflow)
            await s.flush()
            revision = models.WorkflowRevision(workflow_id=workflow.id, increment=1, definition="def")
            s.add(revision)
            await s.flush()
            label = models.Label(key=crud.PROJECT_ID_LABEL_KEY, value="proj-123")
            run = models.WorkflowRun(
                workflow_revision_id=revision.id,
                external_id=external_id,
                lifecycle_status=lifecycle,
                cleanup_policy=schemas.CleanupPolicy.NEVER,
                labels=[label],
            )
            s.add(run)
            await s.commit()
            return run.id

    return _make
