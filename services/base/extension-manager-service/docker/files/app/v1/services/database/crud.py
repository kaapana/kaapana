from uuid import UUID
from typing import Any, List, Optional

from sqlalchemy import select, and_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    RegisteredRepository,
    Extension,
    ExtensionStatus,
    Content,
    ContentStatus,
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
    return result.scalars().all()


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
) -> Optional[RegisteredRepository]:
    values = {}
    if name is not None:
        values["name"] = name
    if description is not None:
        values["description"] = description
    if repository_url is not None:
        values["repository_url"] = repository_url
    if authentication is not None:
        values["authentication"] = authentication
    stmt = (
        update(RegisteredRepository)
        .where(RegisteredRepository.id == id)
        .values(**values)
        .execution_options(synchronize_session="fetch")
    )
    await session.execute(stmt)
    await session.commit()
    return await get_registered_repository(session, id)


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
    return result.scalars().all()


async def update_extension(
    session: AsyncSession, extension_id: UUID, **kwargs: Any
) -> Optional[Extension]:
    stmt = (
        update(Extension)
        .where(Extension.id == extension_id)
        .values(**kwargs)
        .execution_options(synchronize_session="fetch")
    )
    await session.execute(stmt)
    await session.commit()
    return await get_extension(session, extension_id)


async def delete_extension(session: AsyncSession, extension_id: UUID) -> None:
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
) -> Optional[Content]:

    values = {}
    if location:
        values["location"] = location
    if status:
        values["stauts"] = status
    stmt = (
        update(Content)
        .where(Content.id == content_id)
        .values(**values)
        .execution_options(synchronize_session="fetch")
    )
    await session.execute(stmt)
    await session.commit()
    return await get_content(session, content_id)
