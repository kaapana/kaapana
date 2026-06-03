"""Ensure this workflow's own Data API metadata schema is registered.

The worked example of how a workflow adds a **workflow-specific** metadata key to
the Data API: it ships the key's JSON Schema with the workflow and registers it
itself, at run time, from a normal DAG task — rather than entangling the
workflow-installer with the Data API. Cross-cutting/baseline keys the platform
guarantees (``provenance``, ``model``) are shipped data-api-side via an
alembic migration instead; a key only this workflow cares about lives here.

``finetune-note`` is a deliberately small, permissive demo key: enough to show the
registration round-trip and to be attached to the model the demo writes back. The
Data API rejects a metadata POST whose key has no registered schema, so this task
gates the write-back task (see the DAG: ``ensure_schema >> upload_model``).

Idempotent: ``POST /v1/metadata/keys/finetune-note`` registers-or-replaces, so
re-running on every workflow run is harmless.
"""

import asyncio
import logging

from data_api import DataClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ensure-data-schema")

FINETUNE_NOTE_KEY = "finetune-note"

# Permissive draft-07 schema. The `title`s let a UI render friendly labels; the
# demo only needs the key to exist so the write-back can attach a note.
FINETUNE_NOTE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "title": "Finetune Demo Note",
    "description": (
        "Free-form note attached by the data-api fine-tune demo — the example of a "
        "workflow ensuring its own Data API metadata key at run time."
    ),
    "properties": {
        "note": {"type": "string", "title": "Note"},
        "reviewed": {"type": "boolean", "title": "Reviewed"},
    },
    "additionalProperties": True,
}


async def _amain() -> None:
    from kaapanapy.helper import get_project_user_access_token

    access_token = get_project_user_access_token()
    logger.info("Registering (or replacing) '%s' metadata schema", FINETUNE_NOTE_KEY)
    async with DataClient(access_token=access_token) as data:
        await data.register_metadata_schema(FINETUNE_NOTE_KEY, FINETUNE_NOTE_SCHEMA)
    logger.info("Ensured '%s' metadata schema is registered", FINETUNE_NOTE_KEY)


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
