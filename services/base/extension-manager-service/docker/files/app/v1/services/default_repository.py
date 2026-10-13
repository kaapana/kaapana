from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from v1.services import encryption
from v1.services.database import crud
from v1.services.database.models import RegisteredRepository
from v1.services.logger import get_logger

logger = get_logger(__name__)

DEFAULT_REPOSITORY_NAME = "kaapana-default"
DEFAULT_REPOSITORY_DESCRIPTION = "Extensions that are built and published together with the Kaapana platform."


def _has_credentials(repository: RegisteredRepository, username: str, password: str) -> bool:
    try:
        stored = encryption.decrypt(repository.authentication)
    except ValueError:
        # The encryption key can change, for example when its Secret is re-created.
        # The deployment still provides the credentials, so they are encrypted again with the current key.
        logger.warning(f"The credentials of the repository {repository.name} cannot be decrypted. They are replaced.")
        return False
    return stored.get("username") == username and stored.get("password") == password


async def ensure_default_repository(
    session: AsyncSession,
    *,
    url: str,
    username: str,
    password: str,
) -> Optional[RegisteredRepository]:
    """Create the default repository, or update its URL and credentials.

    The repository is identified by its reserved name. The database has no migrations that could add a flag
    column to existing tables. Nothing happens when no URL is given.
    """
    if not url:
        logger.info("No default extension repository is configured.")
        return None

    result = await session.execute(
        select(RegisteredRepository).where(RegisteredRepository.name == DEFAULT_REPOSITORY_NAME)
    )
    repository = result.scalar_one_or_none()

    if repository is None:
        logger.info(f"Registering the default extension repository {url}.")
        return await crud.create_registered_repository(
            session,
            name=DEFAULT_REPOSITORY_NAME,
            description=DEFAULT_REPOSITORY_DESCRIPTION,
            repository_url=url,
            authentication=encryption.encrypt(username, password),
        )

    url_changed = repository.repository_url != url
    if url_changed:
        logger.warning(
            f"The repository {DEFAULT_REPOSITORY_NAME} points to {repository.repository_url}. "
            f"It is changed to the default extension repository {url}."
        )
    # Encryption produces a new token on every call, so the row is only written when something changed.
    if not url_changed and _has_credentials(repository, username, password):
        return repository

    return await crud.update_registered_repository(
        session,
        repository.id,
        repository_url=url,
        authentication=encryption.encrypt(username, password),
    )
