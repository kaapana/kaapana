from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.services.artifact_pruner import prune_orphan_artifacts
from app.services.artifact_store import get_artifact_store

router = APIRouter(prefix="/artifacts", tags=["maintenance"])


class ArtifactPruneResponse(BaseModel):
    scanned_files: int = Field(
        ..., description="Total artifact files discovered on disk"
    )
    deleted_files: int = Field(..., description="Number of orphaned files removed")
    skipped_files: int = Field(
        ..., description="Files that still map to active entities"
    )


@router.post(
    "/prune",
    response_model=ArtifactPruneResponse,
    summary="Delete artifact files that no longer reference live metadata entries",
)
async def prune_artifacts(
    db: AsyncSession = Depends(get_async_db),
) -> ArtifactPruneResponse:
    store = get_artifact_store()
    stats = await prune_orphan_artifacts(db, store)
    return ArtifactPruneResponse(
        scanned_files=stats.scanned_files,
        deleted_files=stats.deleted_files,
        skipped_files=stats.skipped_files,
    )
