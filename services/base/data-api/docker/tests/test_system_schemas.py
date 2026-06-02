"""The platform-shipped system schemas must be valid and self-consistent."""

import json

from jsonschema import Draft7Validator

from app.system_schemas import (
    DATASET_SCHEMA,
    DATASET_SCHEMA_KEY,
    MODEL_SCHEMA,
    MODEL_SCHEMA_KEY,
    PROVENANCE_SCHEMA,
    PROVENANCE_SCHEMA_KEY,
    SYSTEM_SCHEMAS,
)


def test_provenance_schema_is_valid_draft7() -> None:
    # The data-api validates registrations with Draft7Validator.check_schema;
    # a malformed system schema would break the migration that ships it.
    Draft7Validator.check_schema(PROVENANCE_SCHEMA)


def test_provenance_schema_is_json_serialisable() -> None:
    # The alembic migration ships it as a JSONB document.
    assert json.loads(json.dumps(PROVENANCE_SCHEMA)) == PROVENANCE_SCHEMA


def test_provenance_records_execution_context_fields() -> None:
    props = PROVENANCE_SCHEMA["properties"]
    for field in (
        "workflow_name",
        "workflow_run_id",
        "task_id",
        "image",
        "produced_at",
        "project",
        "upstream_entity_ids",
    ):
        assert field in props, f"provenance schema missing '{field}'"
    # Permissive so producers can add context without a schema bump.
    assert PROVENANCE_SCHEMA["additionalProperties"] is True


def test_system_schemas_registry_includes_provenance() -> None:
    assert SYSTEM_SCHEMAS[PROVENANCE_SCHEMA_KEY] is PROVENANCE_SCHEMA


def test_provenance_accepts_a_typical_payload() -> None:
    payload = {
        "workflow_name": "data-api-finetune-demo_v1",
        "workflow_run_id": "manual__2026-05-31T00:00:00+00:00",
        "task_id": "upload_model",
        "image": "registry/data-api-upload:0.0.0",
        "produced_at": "2026-05-31T00:00:00+00:00",
        "project": "admin",
        "upstream_entity_ids": ["a", "b"],
    }
    Draft7Validator(PROVENANCE_SCHEMA).validate(payload)


def test_model_schema_is_valid_draft7() -> None:
    Draft7Validator.check_schema(MODEL_SCHEMA)


def test_model_schema_is_json_serialisable() -> None:
    # The alembic migration ships it as a JSONB document.
    assert json.loads(json.dumps(MODEL_SCHEMA)) == MODEL_SCHEMA


def test_system_schemas_registry_includes_model() -> None:
    assert SYSTEM_SCHEMAS[MODEL_SCHEMA_KEY] is MODEL_SCHEMA


def test_model_is_permissive() -> None:
    # The demo only needs the key to exist; real models carry arbitrary fields.
    assert MODEL_SCHEMA["additionalProperties"] is True


def test_model_accepts_a_typical_payload() -> None:
    payload = {
        "name": "dummy-finetuned-model",
        "framework": "dummy",
        "trained_from_scratch": True,
        "base_model_entity_ids": ["a", "b"],
    }
    Draft7Validator(MODEL_SCHEMA).validate(payload)


def test_dataset_schema_is_valid_draft7() -> None:
    Draft7Validator.check_schema(DATASET_SCHEMA)


def test_dataset_schema_is_json_serialisable() -> None:
    # The alembic migration ships it as a JSONB document.
    assert json.loads(json.dumps(DATASET_SCHEMA)) == DATASET_SCHEMA


def test_system_schemas_registry_includes_dataset() -> None:
    assert SYSTEM_SCHEMAS[DATASET_SCHEMA_KEY] is DATASET_SCHEMA


def test_dataset_is_permissive_with_required_name() -> None:
    # Producers (ingestion DAG, UI, workflow-api) only need the key to exist;
    # extra fields are allowed, but a dataset must at least carry a name.
    assert DATASET_SCHEMA["additionalProperties"] is True
    assert DATASET_SCHEMA["required"] == ["name"]


def test_dataset_accepts_a_typical_payload() -> None:
    Draft7Validator(DATASET_SCHEMA).validate({"name": "cohort-a"})


def test_dataset_rejects_payload_without_name() -> None:
    import pytest
    from jsonschema import ValidationError

    with pytest.raises(ValidationError):
        Draft7Validator(DATASET_SCHEMA).validate({"description": "no name"})
