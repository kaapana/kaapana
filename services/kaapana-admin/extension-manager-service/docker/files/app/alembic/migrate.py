import os

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "")
ALEMBIC_CFG_PATH = "alembic.ini"
INITIAL_REVISION = "fde3423414cf"


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


def main():
    alembic_cfg = Config(ALEMBIC_CFG_PATH)
    script = ScriptDirectory.from_config(alembic_cfg)
    engine = create_engine(DATABASE_URL)

    current_revision = get_current_db_revision(engine)
    print(f"DB is at revision: {current_revision}")

    if current_revision is not None:
        if not is_known_revision(current_revision, script):
            raise SystemExit(
                f"DB revision {current_revision} is not part of the migration chain of this image. "
                "It was probably migrated by a newer image or an image from another branch. "
                "Deploy an image that knows this revision or restore a matching DB backup."
            )
        command.upgrade(alembic_cfg, "head")
    elif is_db_empty(engine):
        print("No revision found in DB and DB is empty. Initializing DB.")
        command.upgrade(alembic_cfg, "head")
    else:
        print("No revision found in DB but DB has tables.")
        print(f"Assuming DB is migrated to 0.7.0. Stamping to revision {INITIAL_REVISION}")
        command.stamp(alembic_cfg, INITIAL_REVISION)
        command.upgrade(alembic_cfg, "head")


if __name__ == "__main__":
    main()
