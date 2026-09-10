"""
Guard for the kaapana-backend Alembic chain.

The startup migration runs `upgrade head`, which refuses to run when the version
files form more than one head - a migration that reuses an existing revision id or
chains onto an old revision does exactly that, and the backend crash-loops. Pin the
chain to its one expected head. No database: the chain is read from the files.
"""

from pathlib import Path

from alembic.script import ScriptDirectory

ALEMBIC_DIR = Path(__file__).resolve().parent.parent / "alembic"


def test_workflow_status_migration_is_the_single_head():
    script = ScriptDirectory(str(ALEMBIC_DIR))

    assert script.get_heads() == ["bf546e91a4dc"]
