from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import BinaryIO, Iterator
from uuid import UUID

from app.config import get_settings


class ArtifactStore:
    """Simple artifact store that persists files under a local directory."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(get_settings().ARTIFACTS_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_component(value: str) -> str:
        return value.replace("/", "_")

    def normalize_components(
        self, entity_id: str | UUID, metadata_key: str, artifact_id: str
    ) -> tuple[str, str, str]:
        return (
            self._safe_component(str(entity_id)),
            self._safe_component(metadata_key),
            self._safe_component(artifact_id),
        )

    def _path_for(
        self, entity_id: str | UUID, metadata_key: str, artifact_id: str
    ) -> Path:
        safe_entity, safe_key, safe_artifact = self.normalize_components(
            entity_id, metadata_key, artifact_id
        )
        return self.base_dir / safe_entity / safe_key / safe_artifact

    def save(
        self,
        entity_id: str | UUID,
        metadata_key: str,
        artifact_id: str,
        fileobj: BinaryIO,
    ) -> Path:
        path = self._path_for(entity_id, metadata_key, artifact_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            f.write(fileobj.read())
        return path

    def open(
        self, entity_id: str | UUID, metadata_key: str, artifact_id: str
    ) -> BinaryIO:
        path = self._path_for(entity_id, metadata_key, artifact_id)
        return path.open("rb")

    def delete_artifact(
        self, entity_id: str | UUID, metadata_key: str, artifact_id: str
    ) -> None:
        path = self._path_for(entity_id, metadata_key, artifact_id)
        path.unlink(missing_ok=True)
        self._cleanup_empty(path.parent)

    def delete_metadata_key(self, entity_id: str | UUID, metadata_key: str) -> None:
        entity_dir = self.base_dir / self._safe_component(str(entity_id))
        key_dir = entity_dir / self._safe_component(metadata_key)
        shutil.rmtree(key_dir, ignore_errors=True)
        self._cleanup_empty(entity_dir)

    def delete_entity(self, entity_id: str | UUID) -> None:
        entity_dir = self.base_dir / self._safe_component(str(entity_id))
        shutil.rmtree(entity_dir, ignore_errors=True)

    def iter_artifact_files(self) -> Iterator[tuple[str, str, str, Path]]:
        if not self.base_dir.exists():
            return
        for entity_dir in self.base_dir.iterdir():
            if not entity_dir.is_dir():
                continue
            for key_dir in entity_dir.iterdir():
                if not key_dir.is_dir():
                    continue
                for artifact_file in key_dir.iterdir():
                    if not artifact_file.is_file():
                        continue
                    yield (
                        entity_dir.name,
                        key_dir.name,
                        artifact_file.name,
                        artifact_file,
                    )

    def delete_path(self, path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
        self._cleanup_empty(path.parent)

    def _cleanup_empty(self, path: Path) -> None:
        current = path
        while current != self.base_dir and current.exists():
            if any(current.iterdir()):
                break
            current.rmdir()
            current = current.parent


_artifact_store: ArtifactStore | None = None


def get_artifact_store() -> ArtifactStore:
    global _artifact_store
    if _artifact_store is None:
        _artifact_store = ArtifactStore()
    return _artifact_store
