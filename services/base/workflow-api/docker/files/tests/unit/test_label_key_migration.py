"""
Unit tests for the migration that renames the extension label keys.
"""

import importlib.util
from pathlib import Path
from types import ModuleType

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from app.models import Base, Label
from sqlalchemy import Engine, create_engine, insert, select

MIGRATION_PATH = Path(__file__).parents[2] / "alembic" / "versions" / "a3b6e8a2a074_rename_extension_label_keys.py"

OLD_LABELS = {
    ("kaapana.immutable.extension.id", "ext-1"),
    ("kaapana.immutable.extension.name", "my-ext"),
    ("kaapana.immutable.extension.version", "1.0.0"),
    ("kaapana.immutable.extension.workflow_name", "my-workflow"),
    ("kaapana-ui.category", "brain"),
}
NEW_LABELS = {
    ("kaapana.immutable.extension.id", "ext-1"),
    ("kaapana.extension.name", "my-ext"),
    ("kaapana.extension.version", "1.0.0"),
    ("kaapana.immutable.extension.content_name", "my-workflow"),
    ("kaapana-ui.category", "brain"),
}


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("rename_extension_label_keys", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _labels(engine: Engine) -> set[tuple[str, str]]:
    with engine.connect() as conn:
        return {(row.key, row.value) for row in conn.execute(select(Label.key, Label.value))}


def test_rename_extension_label_keys_upgrade_and_downgrade():
    migration = _load_migration()
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(insert(Label), [{"key": key, "value": value} for key, value in OLD_LABELS])

    with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
        migration.upgrade()
    assert _labels(engine) == NEW_LABELS

    with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
        migration.downgrade()
    assert _labels(engine) == OLD_LABELS
