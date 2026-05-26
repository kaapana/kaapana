from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import and_, delete, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .exceptions import (
    LockedExtensionException,
    LockedRepositoryException,
    NotSupportedExtensionStateTransition,
    RepositoryExistsException,
)
from .models import (
    ALLOWED_CONTENT_STATUS_TRANSITIONS,
    ALLOWED_EXTENSION_STATUS_TRANSITIONS,
    Content,
    ContentStatus,
    Extension,
    ExtensionStatus,
    RegisteredRepository,
)

# ---------- Reposiory CRUD ----------


async def create_registered_repository(
    session: AsyncSession,
    *,
    name: str,
    description: Optional[str],
    repository_url: str,
    authentication: Optional[str],
) -> RegisteredRepository:
    selection = await session.execute(
        select(RegisteredRepository).where(RegisteredRepository.name == name)
    )
    existing_repo = selection.scalar_one_or_none()
    if existing_repo:
        repository_id = existing_repo.id
        await session.rollback()
        raise RepositoryExistsException(repository_id=repository_id, name=name)
    reg = RegisteredRepository(
        name=name,
        description=description,
        repository_url=repository_url,
        authentication=authentication,
    )
    session.add(reg)
    await session.commit()
    await session.refresh(reg)
    return reg


async def list_registered_repositories(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    repository_id: Optional[UUID] = None,
) -> List[RegisteredRepository]:
    stmt = select(RegisteredRepository)
    filters = []
    if name is not None:
        filters.append(RegisteredRepository.name.ilike(f"%{name}%"))
    if repository_id is not None:
        filters.append(RegisteredRepository.id == repository_id)

    if filters:
        stmt = stmt.where(and_(*filters))
    stmt = stmt.offset(skip).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_registered_repository(
    session: AsyncSession, repository_id: UUID
) -> Optional[RegisteredRepository]:
    result = await session.execute(
        select(RegisteredRepository).where(RegisteredRepository.id == repository_id)
    )
    return result.scalar_one_or_none()


async def update_registered_repository(
    session: AsyncSession,
    id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    repository_url: Optional[str] = None,
    authentication: Optional[str] = None,
) -> RegisteredRepository:
    try:
        result = await session.execute(
            select(RegisteredRepository)
            .where(RegisteredRepository.id == id)
            .with_for_update()
        )
        repo = result.scalar_one()

        if name is not None:
            repo.name = name
        if description is not None:
            repo.description = description
        if repository_url is not None:
            repo.repository_url = repository_url
        if authentication is not None:
            repo.authentication = authentication
        await session.commit()
        await session.refresh(repo)
        return repo
    except OperationalError as e:
        await session.rollback()
        if "could not obtain lock on row" in str(e):
            raise LockedRepositoryException(repository_id=id)
        else:
            raise e


async def delete_registered_repository(
    session: AsyncSession, repository_id: UUID
) -> None:
    stmt = delete(RegisteredRepository).where(RegisteredRepository.id == repository_id)
    await session.execute(stmt)
    await session.commit()


# ---------- Extension CRUD ----------


async def create_extension(
    session: AsyncSession,
    *,
    repository_id: UUID,
    tag: str,
    manifest: dict,
) -> Extension:
    ext = Extension(
        repository_id=repository_id,
        tag=tag,
        manifest=manifest,
        status=ExtensionStatus.PENDING,
    )
    session.add(ext)
    await session.commit()
    await session.refresh(ext)
    return ext


async def get_extension(
    session: AsyncSession, extension_id: UUID
) -> Optional[Extension]:
    result = await session.execute(
        select(Extension)
        .options(selectinload(Extension.contents))
        .where(Extension.id == extension_id)
    )
    return result.scalar_one_or_none()


async def list_extensions(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    repository_id: Optional[UUID] = None,
    tag: Optional[str] = None,
    status: Optional[ExtensionStatus] = None,
) -> List[Extension]:
    stmt = select(Extension).options(selectinload(Extension.contents))
    filters = []
    if repository_id is not None:
        filters.append(Extension.repository_id == repository_id)
    if tag is not None:
        filters.append(Extension.tag.ilike(f"%{tag}%"))
    if status is not None:
        filters.append(Extension.status == status)
    if filters:
        stmt = stmt.where(and_(*filters))
    stmt = stmt.offset(skip).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_extension(
    session: AsyncSession,
    extension_id: UUID,
    status: ExtensionStatus,
) -> Extension:
    try:
        selection = await session.execute(
            select(Extension)
            .where(Extension.id == extension_id)
            .with_for_update(nowait=True)
            .options(selectinload(Extension.contents))
        )
        db_extension = selection.scalar_one()

        if status not in ALLOWED_EXTENSION_STATUS_TRANSITIONS[db_extension.status]:
            raise NotSupportedExtensionStateTransition(
                is_state=db_extension.status, soll_state=status
            )

        db_extension.status = status
        await session.commit()
        await session.refresh(db_extension)
        return db_extension

    except OperationalError as e:
        await session.rollback()
        if "could not obtain lock on row" in str(e):
            raise LockedExtensionException(extension_id=extension_id)
        else:
            raise e


async def delete_extension(session: AsyncSession, extension_id: UUID) -> None:
    db_extension = await get_extension(session, extension_id=extension_id)
    if not db_extension:
        raise Exception(f"Extension not found with id {extension_id}.")
    if db_extension.status is not ExtensionStatus.UNINSTALLED:
        raise Exception(f"Extension in status {db_extension.status} cannot be deleted.")
    stmt = delete(Extension).where(Extension.id == extension_id)
    await session.execute(stmt)
    await session.commit()


# ---------- Content CRUD ----------


async def create_content(
    session: AsyncSession, extension_id: UUID, content_type: str, name: str
) -> Content:
    content = Content(
        name=name,
        extension_id=extension_id,
        content_type=content_type,
        status=ContentStatus.PENDING,
    )

    session.add(content)
    await session.commit()
    await session.refresh(content)
    return content


async def get_content(session: AsyncSession, content_id: UUID) -> Optional[Content]:
    result = await session.execute(select(Content).where(Content.id == content_id))
    return result.scalar_one_or_none()


async def update_content(
    session: AsyncSession,
    content_id: UUID,
    location: Optional[str] = None,
    status: Optional[ContentStatus] = None,
) -> Content:

    try:
        selection = await session.execute(
            select(Content).where(Content.id == content_id).with_for_update(nowait=True)
        )
        db_content = selection.scalar_one()
        if (
            status
            and status not in ALLOWED_CONTENT_STATUS_TRANSITIONS[db_content.status]
        ):
            raise Exception(
                f"Invalid status transition from {db_content.status} to {status} for content with id {content_id}"
            )
        elif status:
            db_content.status = status
        if location and location != db_content.location:
            db_content.location = location
        await session.commit()
        await session.refresh(db_content)
        return db_content

    except OperationalError as e:
        await session.rollback()
        if "could not obtain lock on row" in str(e):
            raise Exception(
                f"Content with id {content_id} is currently being updated by another process. Please try again later."
            ) from e
        else:
            raise e
