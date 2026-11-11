# The environment and the JSONB shim below must be in place before the app modules import.
# ruff: noqa: E402
import os

import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, event
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

postgresql.JSONB = JSON
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())

from unittest.mock import AsyncMock, MagicMock, patch

from main import app
from v1.services.database import crud
from v1.services.database.database import get_async_db
from v1.services.database.models import Base
from v1.services.dispatch.content import Content, ContentInstaller, InstallationResult


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


import json
import shutil
import tarfile
import tempfile
from pathlib import Path
from uuid import UUID

from v1.routers.dependencies import get_oci_service_for_repository
from v1.services import encryption, upload
from v1.services.oci.exceptions import ExtensionNotFoundException
from v1.services.oci.mock_service import ociService as MockOciService
from v1.services.oci.models import ExtensionManifest

UPLOAD_REGISTRY_URL = "http://extension-registry.test:5000/uploads"


class FakeUploadRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.repository_url = UPLOAD_REGISTRY_URL

    async def __aenter__(self) -> "FakeUploadRegistry":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def get_extensions_for_repository(self) -> set[str]:
        return {path.name for path in self.root.iterdir()}

    async def get_extension_manifests(self, tags: set[str] | None = None) -> dict[str, ExtensionManifest]:
        existing_tags = await self.get_extensions_for_repository()
        selected_tags = existing_tags & tags if tags else existing_tags
        return {tag: await self.get_extension_manifest(tag) for tag in selected_tags}

    async def get_extension_manifest(self, tag: str) -> ExtensionManifest:
        if tag not in await self.get_extensions_for_repository():
            raise ExtensionNotFoundException(f"Extension with tag {tag} not found in {self.repository_url}")
        return ExtensionManifest(**json.loads((self.root / tag / upload.MANIFEST_FILE).read_text()))

    async def pull_extension(self, tag: str) -> Path:
        if tag not in await self.get_extensions_for_repository():
            raise ExtensionNotFoundException(f"Extension with tag {tag} not found in {self.repository_url}")
        target = Path(tempfile.mkdtemp()) / tag
        shutil.copytree(self.root / tag, target)
        return target

    async def push_extension(self, archive: Path) -> str:
        with tarfile.open(archive, "r:gz") as tar:
            manifest = json.loads(tar.extractfile(upload.MANIFEST_FILE).read())
            tag = f"{manifest['id']}-v{manifest['version']}"
            shutil.rmtree(self.root / tag, ignore_errors=True)
            tar.extractall(self.root / tag, filter="data")
        return tag

    async def delete_extension(self, tag: str) -> None:
        if tag not in await self.get_extensions_for_repository():
            raise ExtensionNotFoundException(f"Extension with tag {tag} not found in {self.repository_url}")
        shutil.rmtree(self.root / tag)


@pytest_asyncio.fixture(name="upload_registry")
def upload_registry_fixture(tmp_path: Path) -> FakeUploadRegistry:
    root = tmp_path / "upload-registry"
    root.mkdir()
    return FakeUploadRegistry(root)


@pytest_asyncio.fixture(name="mock_ociService", autouse=True)
async def mock_ociService(session: AsyncSession, upload_registry: FakeUploadRegistry):
    def service(repository_url: str, authentication: str):
        if repository_url == UPLOAD_REGISTRY_URL:
            return upload_registry
        return MockOciService(repository_url=repository_url, authentication=authentication)

    async def override(repository_id: UUID):
        repository = await crud.get_registered_repository(session, repository_id)
        if not repository:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
        if upload.is_upload_repository(repository_id):
            async with upload_registry as svc:
                yield svc
            return
        async with MockOciService(repository_url="test", authentication=encryption.encrypt("", "")) as svc:
            yield svc

    app.dependency_overrides[get_oci_service_for_repository] = override

    with patch("v1.routers.dependencies.ociService", new=service):
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
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
