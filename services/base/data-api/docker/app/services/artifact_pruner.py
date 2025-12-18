from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ArtifactORM, DataEntityORM, MetadataEntryORM
from app.services.artifact_store import ArtifactStore


@dataclass
class ArtifactPruneStats:
    scanned_files: int
    deleted_files: int

    @property
    def skipped_files(self) -> int:
        return max(self.scanned_files - self.deleted_files, 0)


async def prune_orphan_artifacts(
    db: AsyncSession, store: ArtifactStore
) -> ArtifactPruneStats:
    stmt = (
        select(DataEntityORM.id, MetadataEntryORM.key, ArtifactORM.artifact_id)
        .join(MetadataEntryORM, MetadataEntryORM.entity_id == DataEntityORM.id)
        .join(ArtifactORM, ArtifactORM.metadata_entry_id == MetadataEntryORM.id)
    )
    result = await db.execute(stmt)
    valid = {
        store.normalize_components(str(entity_id), key, artifact_id)
        for entity_id, key, artifact_id in result.all()
    }

    scanned = deleted = 0
    for safe_entity, safe_key, safe_artifact, path in store.iter_artifact_files():
        scanned += 1
        if (safe_entity, safe_key, safe_artifact) in valid:
            continue
        store.delete_path(path)
        deleted += 1

    return ArtifactPruneStats(scanned_files=scanned, deleted_files=deleted)
