import os

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "")
ALEMBIC_CFG_PATH = "alembic.ini"
INITIAL_REVISION = "721d0352a128"


def get_current_db_revision(engine):
    with engine.connect() as conn:
        inspector = inspect(conn)
        if "alembic_version" not in inspector.get_table_names():
            return None
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        row = result.fetchone()
        return row[0] if row else None


def is_known_revision(revision: str, script_dir: ScriptDirectory) -> bool:
    return revision in {rev.revision for rev in script_dir.walk_revisions()}


def is_db_empty(engine):
    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = inspector.get_table_names()
        return len(tables) == 0


def _detect_legacy_schema(engine) -> str | None:
    """
    Identify a DB created by `Base.metadata.create_all` without Alembic.

    Returns the revision that matches the on-disk schema so it can be stamped.
    """
    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
    if "workflows" not in tables:
        return None
    if "workflow_revisions" in tables:
        return "4f9a2b1d7e3c"
    return INITIAL_REVISION


def main():
    alembic_cfg = Config(ALEMBIC_CFG_PATH)
    script = ScriptDirectory.from_config(alembic_cfg)
    engine = create_engine(DATABASE_URL)

    current_revision = get_current_db_revision(engine)
    print(f"DB is at revision: {current_revision}")

    if is_known_revision(current_revision, script):
        command.upgrade(alembic_cfg, "head")
        return
    if is_db_empty(engine):
        print("No revision found in DB and DB is empty. Initializing DB.")
        command.upgrade(alembic_cfg, "head")
        return

    legacy_rev = _detect_legacy_schema(engine)
    if legacy_rev is not None:
        print(
            f"DB has tables but no alembic_version. Stamping as {legacy_rev} and upgrading to head."
        )
        command.stamp(alembic_cfg, legacy_rev)
        command.upgrade(alembic_cfg, "head")
        return

    print("DB revision is not part of current migration chain!")


if __name__ == "__main__":
    main()
