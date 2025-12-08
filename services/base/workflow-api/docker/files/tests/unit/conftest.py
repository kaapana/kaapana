"""
Test configuration following SQLModel testing patterns.
Uses pytest fixtures with in-memory SQLite database.
"""

import os
import sys
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test database URL BEFORE any imports
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# Monkey-patch JSONB to JSON for SQLite BEFORE importing models
from sqlalchemy import JSON
from sqlalchemy.dialects import postgresql

postgresql.JSONB = JSON

# Add parent directories to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.dependencies import get_async_db
from app.main import app
from app.models import Base


def pytest_configure(config):
    """Register custom markers for test routes."""
    # HTTP method markers
    config.addinivalue_line("markers", "GET: Tests for GET requests")
    config.addinivalue_line("markers", "POST: Tests for POST requests")
    config.addinivalue_line("markers", "PUT: Tests for PUT requests")
    config.addinivalue_line("markers", "DELETE: Tests for DELETE requests")
    
    # Route-specific markers
    config.addinivalue_line("markers", "post_workflows: Tests for POST /v1/workflows")
    config.addinivalue_line("markers", "get_workflows: Tests for GET /v1/workflows")
    config.addinivalue_line("markers", "get_workflow_by_title: Tests for GET /v1/workflows/{title}")
    config.addinivalue_line("markers", "get_workflow_by_title_version: Tests for GET /v1/workflows/{title}/{version}")
    config.addinivalue_line("markers", "delete_workflow: Tests for DELETE /v1/workflows/{title}/{version}")
    config.addinivalue_line("markers", "get_workflow_tasks: Tests for GET /v1/workflows/{title}/{version}/tasks")
    config.addinivalue_line("markers", "get_task: Tests for GET /v1/workflows/{title}/{version}/tasks/{task_title}")
    config.addinivalue_line("markers", "post_workflow_runs: Tests for POST /v1/workflow-runs")
    config.addinivalue_line("markers", "get_workflow_runs: Tests for GET /v1/workflow-runs")
    config.addinivalue_line("markers", "get_workflow_run_by_id: Tests for GET /v1/workflow-runs/{id}")
    config.addinivalue_line("markers", "cancel_workflow_run: Tests for PUT /v1/workflow-runs/{id}/cancel")
    config.addinivalue_line("markers", "retry_workflow_run: Tests for PUT /v1/workflow-runs/{id}/retry")
    config.addinivalue_line("markers", "get_workflow_run_task_runs: Tests for GET /v1/workflow-runs/{id}/task-runs")
    config.addinivalue_line("markers", "get_task_run: Tests for GET /v1/workflow-runs/{id}/task-runs/{task_run_id}")
    config.addinivalue_line("markers", "get_task_run_logs: Tests for GET /v1/workflow-runs/{id}/task-runs/{task_run_id}/logs")


@pytest_asyncio.fixture(name="session")
async def session_fixture():
    """
    Create a fresh in-memory async database session for each test.

    Following SQLModel pattern:
    - In-memory SQLite (fast, isolated)
    - Fresh database for each test
    - Automatic cleanup after test
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session maker
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Yield session for test
    async with async_session_maker() as session:
        yield session

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(name="client")
async def client_fixture(session: AsyncSession):
    """
    Create a test client with overridden database dependency.

    Following SQLModel pattern:
    - Override get_async_db dependency to use test session
    - Clear overrides after test
    - Client can make HTTP requests to test API
    """

    async def get_async_db_override():
        yield session

    app.dependency_overrides[get_async_db] = get_async_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
