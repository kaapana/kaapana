from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import startup
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from v1.services import encryption
from v1.services.database import crud
from v1.services.database.models import RegisteredRepository
from v1.services.default_repository import DEFAULT_REPOSITORY_NAME, ensure_default_repository

URL = "https://registry.example.com/kaapana/extensions"


async def _repositories(session: AsyncSession) -> list[RegisteredRepository]:
    result = await session.execute(select(RegisteredRepository))
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_creates_default_repository(session: AsyncSession):
    repository = await ensure_default_repository(session, url=URL, username="user", password="secret")

    assert repository.name == DEFAULT_REPOSITORY_NAME
    assert repository.repository_url == URL
    assert encryption.decrypt(repository.authentication) == {"username": "user", "password": "secret"}


@pytest.mark.asyncio
async def test_second_call_keeps_the_row(session: AsyncSession):
    first = await ensure_default_repository(session, url=URL, username="user", password="secret")
    authentication = first.authentication

    second = await ensure_default_repository(session, url=URL, username="user", password="secret")

    assert [repository.id for repository in await _repositories(session)] == [first.id]
    assert second.authentication == authentication


@pytest.mark.asyncio
async def test_updates_url_and_credentials(session: AsyncSession):
    first = await ensure_default_repository(session, url=URL, username="user", password="secret")

    new_url = "https://other.example.com/kaapana/extensions"
    updated = await ensure_default_repository(session, url=new_url, username="other", password="changed")

    assert updated.id == first.id
    assert updated.repository_url == new_url
    assert encryption.decrypt(updated.authentication) == {"username": "other", "password": "changed"}


@pytest.mark.asyncio
async def test_updates_changed_password_only(session: AsyncSession):
    await ensure_default_repository(session, url=URL, username="user", password="secret")

    updated = await ensure_default_repository(session, url=URL, username="user", password="changed")

    assert encryption.decrypt(updated.authentication) == {"username": "user", "password": "changed"}


@pytest.mark.asyncio
async def test_replaces_credentials_encrypted_with_another_key(session: AsyncSession):
    other_key = Fernet(Fernet.generate_key())
    await crud.create_registered_repository(
        session,
        name=DEFAULT_REPOSITORY_NAME,
        description="",
        repository_url=URL,
        authentication=other_key.encrypt(b'{"username": "user", "password": "secret"}').decode(),
    )

    repository = await ensure_default_repository(session, url=URL, username="user", password="secret")

    assert encryption.decrypt(repository.authentication) == {"username": "user", "password": "secret"}


@pytest.mark.asyncio
async def test_empty_url_creates_nothing(session: AsyncSession):
    assert await ensure_default_repository(session, url="", username="user", password="secret") is None
    assert await _repositories(session) == []


@pytest.mark.asyncio
async def test_other_repositories_stay_unchanged(session: AsyncSession):
    other = await crud.create_registered_repository(
        session,
        name="my-repository",
        description="",
        repository_url="https://example.com/mine",
        authentication=encryption.encrypt("me", "mine"),
    )

    await ensure_default_repository(session, url=URL, username="user", password="secret")

    await session.refresh(other)
    assert other.repository_url == "https://example.com/mine"
    assert encryption.decrypt(other.authentication) == {"username": "me", "password": "mine"}
    assert len(await _repositories(session)) == 2


@pytest.mark.asyncio
async def test_takes_over_existing_row_with_reserved_name(session: AsyncSession):
    existing = await crud.create_registered_repository(
        session,
        name=DEFAULT_REPOSITORY_NAME,
        description="",
        repository_url="https://example.com/mine",
        authentication=encryption.encrypt("me", "mine"),
    )

    with patch("v1.services.default_repository.logger") as logger:
        repository = await ensure_default_repository(session, url=URL, username="user", password="secret")

    assert repository.id == existing.id
    assert repository.repository_url == URL
    logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_startup_registers_default_repository(session: AsyncSession, monkeypatch):
    monkeypatch.setenv("DEFAULT_EXTENSION_REPOSITORY_URL", URL)
    monkeypatch.setenv("DEFAULT_EXTENSION_REPOSITORY_USERNAME", "user")
    monkeypatch.setenv("DEFAULT_EXTENSION_REPOSITORY_PASSWORD", "secret")

    await startup.main()

    repositories = await _repositories(session)
    assert [repository.repository_url for repository in repositories] == [URL]


@pytest.mark.asyncio
async def test_startup_survives_a_seeding_error(session: AsyncSession, monkeypatch):
    monkeypatch.setenv("DEFAULT_EXTENSION_REPOSITORY_URL", URL)
    failing = AsyncMock(side_effect=RuntimeError("database is gone"))

    with (
        patch("startup.ensure_default_repository", new=failing),
        patch("startup.logger", new=MagicMock()) as logger,
    ):
        await startup.main()

    failing.assert_awaited_once()
    logger.exception.assert_called_once()
