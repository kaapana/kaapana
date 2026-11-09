from uuid import UUID

from fastapi import Depends, HTTPException, status
from v1.services import upload
from v1.services.database import crud
from v1.services.database.database import AsyncSession, get_async_db
from v1.services.database.models import RegisteredRepository
from v1.services.oci.service import ociService


def repository_service(repository: RegisteredRepository) -> ociService | upload.UploadRepositoryService:
    if upload.is_upload_repository(repository.id):
        return upload.UploadRepositoryService()
    return ociService(
        repository_url=repository.repository_url,
        authentication=repository.authentication,
    )


async def get_oci_service_for_repository(repository_id: UUID, db: AsyncSession = Depends(get_async_db)):
    repository = await crud.get_registered_repository(db, repository_id)
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    async with repository_service(repository) as service:
        yield service
