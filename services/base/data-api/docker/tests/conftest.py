import json
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:55432/test")
os.environ.setdefault("ARTIFACTS_DIR", tempfile.mkdtemp(prefix="data-api-artifacts-"))

from app.db.models import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

PROJECT_A = "aaaaaaaa-0000-0000-0000-000000000001"
PROJECT_B = "bbbbbbbb-0000-0000-0000-000000000002"


def project_header(project_id: str) -> dict[str, str]:
    return {"Project": json.dumps({"id": project_id, "name": f"project-{project_id[:4]}", "short_id": project_id[:8]})}


def entity_payload(project_id: str | None = None, **metadata: dict) -> dict:
    entries = [{"key": key, "data": data, "artifacts": []} for key, data in metadata.items()]
    if project_id is not None:
        entries.append({"key": "permissions", "data": {"project": project_id, "owner": None}, "artifacts": []})
    return {"id": str(uuid4()), "storage_coordinates": [], "metadata": entries}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    await engine.dispose()
