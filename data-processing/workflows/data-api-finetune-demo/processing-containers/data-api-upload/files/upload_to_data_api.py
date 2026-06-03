"""Store-agnostic write-back task — the mirror image of ``data-api-download``.

Reads the files produced by an upstream task on its input channel plus an
``upload_manifest.json`` control file, then:

1. uploads the files to the target store via the storage-api (``StorageClient``)
   — model files / arbitrary bytes go to S3; DICOM would STOW-RS to PACS — and
   gets back concrete storage coordinates;
2. mints a NEW Data API entity carrying those coordinates;
3. attaches the manifest's domain metadata (e.g. ``model-card``);
4. stamps a ``provenance`` entry from the trusted run-context env injected by the
   KaapanaTaskOperator (which workflow / run / task / image), plus the manifest's
   upstream entity IDs (lineage).

Provenance is operator-owned: it is built from env the platform injects, never
read from the manifest, so a producing task cannot forge "who made this". (This
is a discovery convention, not an enforced guarantee — see DATA_API.md.) The
storage-api never touches the Data API; this task is the only place the two meet.
"""

import argparse
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from data_api import DataClient, StorageClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("data-api-upload")

UPLOAD_MANIFEST_NAME = "upload_manifest.json"
PROVENANCE_KEY = "provenance"

# The project bucket ("project-{short_id}") is shared with all other project data
# (incoming DICOM, workflow results, app I/O). Namespace every data-api write under
# this top-level prefix so it never collides with the rest of the bucket.
DATA_API_PREFIX = "data-api"


def _collect_files(channel: Path) -> List[Tuple[str, bytes]]:
    """Read every file under ``channel`` except the manifest control file."""
    files: List[Tuple[str, bytes]] = []
    for path in sorted(channel.rglob("*")):
        if path.is_file() and path.name != UPLOAD_MANIFEST_NAME:
            files.append((path.relative_to(channel).as_posix(), path.read_bytes()))
    return files


def _require_run_context() -> None:
    """Fail loud if the operator-injected run-context env is absent.

    The whole bootstrap loop hinges on a non-empty ``provenance.workflow_name``
    (the next run's model picker is scoped by it). If the KaapanaTaskOperator's
    env injection didn't reach the pod, an upload would otherwise succeed with
    empty provenance and the model would be SILENTLY unselectable next run — the
    worst failure to debug. These vars are always present in a real Task-API pod,
    so this guard only fires when something is genuinely broken.
    """
    missing = [
        key
        for key in ("KAAPANA_DAG_ID", "KAAPANA_WORKFLOW_RUN_ID")
        if not os.environ.get(key)
    ]
    if missing:
        raise RuntimeError(
            f"Missing run-context env {missing}; the KaapanaTaskOperator must inject "
            "it. Refusing to write a model with empty provenance (it would be "
            "unselectable on the next run)."
        )


def _build_provenance(upstream_entity_ids: List[str]) -> dict:
    """Assemble provenance from trusted run-context env (operator-injected)."""
    return {
        "workflow_name": os.environ.get("KAAPANA_DAG_ID", ""),
        "workflow_run_id": os.environ.get("KAAPANA_WORKFLOW_RUN_ID", ""),
        "task_id": os.environ.get("KAAPANA_TASK_ID", ""),
        "image": os.environ.get("KAAPANA_IMAGE", ""),
        "produced_at": datetime.now(timezone.utc).isoformat(),
        "project": os.environ.get("KAAPANA_PROJECT_IDENTIFIER", ""),
        "upstream_entity_ids": upstream_entity_ids,
    }


def _project_bucket() -> str:
    """Infer the project MinIO bucket from ``KAAPANA_PROJECT_IDENTIFIER``.

    Re-derives AII's ``Project.s3_bucket`` convention locally — ``project-{short_id}``
    where ``short_id = uuid.hex[:8]`` — instead of having workflow-api thread the
    authoritative bucket through. The identifier injected by the operator is the
    project UUID; if it is already a short_id, an explicit ``project-…`` bucket, or
    the literal ``"admin"``, it is used as-is.

    CAVEAT (intentional, dirty): the admin project's bucket is ``project-admin``,
    which is NOT derivable from its UUID. If this workflow runs in the admin
    project, set ``UPLOAD_S3_BUCKET=project-admin`` explicitly.
    """
    identifier = os.environ.get("KAAPANA_PROJECT_IDENTIFIER", "").strip()
    if not identifier:
        return ""
    if identifier == "admin":
        return "project-admin"
    if identifier.startswith("project-"):
        return identifier
    try:
        short_id = uuid.UUID(identifier).hex[:8]
    except ValueError:
        short_id = identifier  # already a short_id / custom name
    return f"project-{short_id}"


def _s3_target(entity_id: str) -> dict:
    """Bucket + per-run key prefix for the model bytes.

    Bucket: explicit ``UPLOAD_S3_BUCKET`` override, else the project bucket inferred
    from ``KAAPANA_PROJECT_IDENTIFIER`` (see ``_project_bucket``). The project
    web-identity role's ``admin_project`` MinIO policy already grants PutObject on
    ``arn:aws:s3:::project-{short_id}/*``; the key is namespaced under
    ``DATA_API_PREFIX`` because the bucket is shared with other project data.
    """
    bucket = os.environ.get("UPLOAD_S3_BUCKET") or _project_bucket()
    if not bucket:
        raise RuntimeError(
            "No S3 bucket: set UPLOAD_S3_BUCKET or KAAPANA_PROJECT_IDENTIFIER"
        )
    dag_id = os.environ.get("KAAPANA_DAG_ID", "workflow")
    run_id = os.environ.get("KAAPANA_WORKFLOW_RUN_ID", "run")
    return {
        "bucket": bucket,
        "key_prefix": f"{DATA_API_PREFIX}/models/{dag_id}/{run_id}/{entity_id}/",
    }


async def _amain() -> None:
    from kaapanapy.helper import get_project_user_access_token

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--input", type=Path, default=Path("/home/kaapana/results")
    )
    args = parser.parse_args()

    # Fail before writing any bytes if provenance would be empty.
    _require_run_context()

    manifest_path = args.input / UPLOAD_MANIFEST_NAME
    if not manifest_path.is_file():
        raise RuntimeError(
            f"No {UPLOAD_MANIFEST_NAME} on the input channel {args.input}"
        )
    manifest = json.loads(manifest_path.read_text())

    files = _collect_files(args.input)
    if not files:
        raise RuntimeError(f"No files to upload on the input channel {args.input}")
    logger.info("Collected %d file(s) from input channel %s", len(files), args.input)

    entity_id = str(uuid.uuid4())
    store = manifest.get("store", "s3")
    # "folder" (default): the artifact is the whole channel, stored under one prefix
    # and addressed by a single folder coordinate. "file": exactly one file, addressed
    # by a single object coordinate.
    unit = manifest.get("unit", "folder")
    if unit not in ("file", "folder"):
        raise RuntimeError(f"Manifest 'unit' must be 'file' or 'folder', got {unit!r}")
    if unit == "file" and len(files) != 1:
        raise RuntimeError(
            f"Manifest declares unit 'file' but {len(files)} files are on the input "
            f"channel {args.input}; use 'folder' for multi-file artifacts"
        )
    target = _s3_target(entity_id) if store == "s3" else manifest.get("target", {})
    if store == "s3":
        target = {**target, "unit": unit}

    access_token = get_project_user_access_token()
    async with DataClient(access_token=access_token) as data, StorageClient(
        access_token=access_token
    ) as storage:
        # Bytes first: a later failure orphans a GC-able object, not a dangling
        # coordinate. The returned coordinates are already in the Data API's
        # flat coordinate shape (type + store fields).
        logger.info(
            "Uploading bytes to store=%s (unit=%s) for entity %s",
            store,
            unit,
            entity_id,
        )
        coordinates = await storage.upload(files, store=store, target=target)

        logger.info("Creating Data API entity %s", entity_id)
        await data.create_entity(
            {"id": entity_id, "storage_coordinates": coordinates, "metadata": []}
        )
        for key, value in manifest.get("metadata", {}).items():
            logger.info("Attaching metadata '%s' to entity %s", key, entity_id)
            await data.attach_metadata(entity_id, key, value)
        await data.attach_metadata(
            entity_id,
            PROVENANCE_KEY,
            _build_provenance(manifest.get("upstream_entity_ids", [])),
        )

    logger.info(
        "Wrote back entity %s (%d file(s), store=%s, unit=%s) with metadata %s + provenance",
        entity_id,
        len(files),
        store,
        unit,
        list(manifest.get("metadata", {})),
    )


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
