import os

import pytest_asyncio
from fastapi import Depends, HTTPException, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, event
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

postgresql.JSONB = JSON
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from unittest.mock import AsyncMock, MagicMock, patch

from main import app
from v1.services.database import crud
from v1.services.database.database import get_async_db
from v1.services.database.models import Base
from v1.services.dispatch.content import Content, ContentInstaller, InstallationResult
from v1.services.dispatch.dispatcher import Dispatcher


class MockedInstaller(ContentInstaller):
    def can_install(self, content: Content) -> bool:
        return True

    async def install(self, content: Content) -> InstallationResult:
        return InstallationResult(
            success=True,
            message="Mocked installation successful",
            location="/mock/location",
        )

    async def uninstall(self, content: Content) -> None:
        pass


@pytest_asyncio.fixture(name="mocked_installer")
def mocked_installer():
    """
    Mock the dispatcher to use a MockContentInstaller
    """
    mock_dispatcher = MagicMock()
    mock_dispatcher.install_content = AsyncMock(
        return_value=InstallationResult(
            success=True,
            message="Mocked installation successful",
            location="/mock/location",
        )
    )
    mock_dispatcher._find_installer = MagicMock(return_value=MockedInstaller())
    mock_dispatcher.uninstall_content = AsyncMock(return_value=None)
    with patch("v1.services.dispatch.dispatcher", new=mock_dispatcher):

        yield mock_dispatcher


from uuid import UUID

from v1.routers.dependencies import get_oci_service_for_repository
from v1.services.oci.mock_service import ociService as MockOciService


@pytest_asyncio.fixture(name="mock_ociService", autouse=True)
async def mock_ociService(session: AsyncSession):
    async def override(repository_id: UUID):
        repository = await crud.get_registered_repository(session, repository_id)
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
            )
        async with MockOciService(repository_url="test", authentication="") as svc:
            yield svc

    app.dependency_overrides[get_oci_service_for_repository] = override

    with patch(
        "v1.routers.installation.background_jobs.ociService", new=MockOciService
    ):
        yield

    app.dependency_overrides.pop(get_oci_service_for_repository, None)


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

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session maker
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Yield session for test
    with patch("v1.services.database.database.async_session", new=async_session_maker):
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
