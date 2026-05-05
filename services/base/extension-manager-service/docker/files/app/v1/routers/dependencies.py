from v1.services.oci.service import ociService
from v1.services.database.database import get_async_db, AsyncSession
import uuid
from fastapi import Depends, HTTPException, status

from v1.services.database.crud import get_registered_repository


async def get_oci_service_for_repository(
    repository_id: uuid.UUID, db: AsyncSession = Depends(get_async_db)
):
    repository = await get_registered_repository(db, repository_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )

    async with ociService(
        repository_url=repository.repository_url,
        authentication=repository.authentication,
    ) as oci_service:
        yield oci_service
