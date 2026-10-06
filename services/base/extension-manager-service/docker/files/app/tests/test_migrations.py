from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine
from v1.services.database.models import Base

APP_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(name="db_path")
def db_path_fixture(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "extension_manager.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    return path


@pytest.fixture(name="alembic_cfg")
def alembic_cfg_fixture(db_path: Path) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(APP_DIR / "alembic"))
    return cfg


def test_head_matches_the_models(alembic_cfg: Config, db_path: Path):
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": False}), Base.metadata)
    engine.dispose()

    assert diff == []
