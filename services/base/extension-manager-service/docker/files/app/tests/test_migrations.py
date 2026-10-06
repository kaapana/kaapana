import sqlite3
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine
from v1.services.database.models import Base

APP_DIR = Path(__file__).resolve().parents[1]
INITIAL_REVISION = "fde3423414cf"


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


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def test_upgrade_from_0_7_keeps_extensions_when_their_repository_is_removed(alembic_cfg: Config, db_path: Path):
    command.upgrade(alembic_cfg, INITIAL_REVISION)

    repository_id, extension_id, content_id = (uuid.uuid4().hex for _ in range(3))
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO registries (id, name, description, repository_url, authentication) VALUES (?, ?, ?, ?, ?)",
            (repository_id, "Test Repository", "", "https://example.com/oci", "secret"),
        )
        conn.execute(
            "INSERT INTO extensions (id, repository_id, tag, manifest, status) VALUES (?, ?, ?, ?, ?)",
            (extension_id, repository_id, "1.0.0", "{}", "installed"),
        )
        conn.execute(
            "INSERT INTO contents (id, extension_id, name, content_type, status) VALUES (?, ?, ?, ?, ?)",
            (content_id, extension_id, "chart", "helm", "installed"),
        )

    command.upgrade(alembic_cfg, "head")

    with _connect(db_path) as conn:
        assert conn.execute("SELECT repository_id, status FROM extensions").fetchall() == [(repository_id, "installed")]
        conn.execute("DELETE FROM registries WHERE id = ?", (repository_id,))
        assert conn.execute("SELECT id, repository_id FROM extensions").fetchall() == [(extension_id, None)]
        assert conn.execute("SELECT id FROM contents").fetchall() == [(content_id,)]


def test_head_matches_the_models(alembic_cfg: Config, db_path: Path):
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": False}), Base.metadata)
    engine.dispose()

    assert diff == []


def test_downgrade_to_0_7_restores_the_cascade(alembic_cfg: Config, db_path: Path):
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, INITIAL_REVISION)

    repository_id = uuid.uuid4().hex
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO registries (id, name, description, repository_url, authentication) VALUES (?, ?, ?, ?, ?)",
            (repository_id, "Test Repository", "", "https://example.com/oci", "secret"),
        )
        conn.execute(
            "INSERT INTO extensions (id, repository_id, tag, manifest, status) VALUES (?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, repository_id, "1.0.0", "{}", "installed"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO extensions (id, repository_id, tag, manifest, status) VALUES (?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, None, "2.0.0", "{}", "installed"),
            )
        conn.execute("DELETE FROM registries WHERE id = ?", (repository_id,))
        assert conn.execute("SELECT COUNT(*) FROM extensions").fetchone() == (0,)
