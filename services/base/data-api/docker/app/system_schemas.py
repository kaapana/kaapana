"""Platform-shipped ("system") metadata schemas.

These are the schemas the Data API guarantees are present on every install,
registered via an alembic data-migration rather than by a runtime producer.

``provenance`` records the execution context that produced an entity — which
workflow / run / task / image, when, in which project, and the upstream entity
IDs it derived from. A tool can then *discover* entities by producer (e.g. the
fine-tune demo scoping selectable models to those its own workflow produced).
"""

from __future__ import annotations

PROVENANCE_SCHEMA_KEY = "provenance"

PROVENANCE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "title": "Provenance",
    "description": (
        "Execution context that produced this entity (workflow/run/task/image, "
        "project, time) plus the upstream entity IDs it derived from."
    ),
    "properties": {
        "workflow_name": {
            "type": "string",
            "description": "Producing workflow identifier (Airflow dag_id).",
        },
        "workflow_run_id": {
            "type": "string",
            "description": "Producing workflow run identifier (Airflow run_id).",
        },
        "task_id": {"type": "string", "description": "Producing task identifier."},
        "image": {"type": "string", "description": "Producing operator image."},
        "produced_at": {
            "type": "string",
            "format": "date-time",
            "description": "ISO-8601 timestamp the entity was produced.",
        },
        "project": {"type": "string", "description": "Owning project identifier."},
        "upstream_entity_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Entity IDs this entity was derived from (lineage).",
        },
    },
    # Permissive: producers may record extra context without a schema bump.
    "additionalProperties": True,
}

SYSTEM_SCHEMAS = {
    PROVENANCE_SCHEMA_KEY: PROVENANCE_SCHEMA,
}
