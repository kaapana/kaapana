from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.dependencies import get_async_db, get_connection_manager
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

client = TestClient(app)
HEADERS = {"X-Forwarded-User": "alice"}


def sql(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))


@pytest.fixture
def fake(request):
    """Session double that records statements and answers RETURNING with `ids`."""
    ids = getattr(request, "param", [uuid4(), uuid4()])
    statements = []

    async def execute(stmt):
        statements.append(stmt)
        result = MagicMock()
        result.scalars.return_value.all.return_value = ids
        return result

    db = MagicMock(execute=AsyncMock(side_effect=execute), commit=AsyncMock())
    con_mgr = MagicMock(notify_read_all=AsyncMock())

    async def override_db():
        yield db

    app.dependency_overrides[get_async_db] = override_db
    app.dependency_overrides[get_connection_manager] = lambda: con_mgr
    yield SimpleNamespace(ids=ids, statements=statements, db=db, con_mgr=con_mgr)
    app.dependency_overrides.clear()


def test_marks_every_unread_notification_of_the_caller(fake):
    response = client.put("/v2/read", headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == [str(i) for i in fake.ids]
    stmt = fake.statements[0]
    text = sql(stmt)
    assert text.startswith("UPDATE notifications SET receviers_read=jsonb_set(")
    assert "= ANY (notifications.receivers)" in text
    assert "NOT (notifications.receviers_read ? " in text
    assert text.endswith("RETURNING notifications.id")
    assert "alice" in stmt.compile(dialect=postgresql.dialect()).params.values()
    fake.db.commit.assert_awaited_once()


def test_drops_notifications_every_recipient_has_read(fake):
    client.put("/v2/read", headers=HEADERS)

    text = sql(fake.statements[1])
    assert text.startswith("DELETE FROM notifications WHERE notifications.id IN (")
    assert text.endswith("AND notifications.receviers_read ?& notifications.receivers")


def test_sends_one_read_all_event(fake):
    client.put("/v2/read", headers=HEADERS)

    fake.con_mgr.notify_read_all.assert_awaited_once_with(user_ids=["alice"])


@pytest.mark.parametrize("fake", [[]], indirect=True)
def test_nothing_unread_is_a_no_op(fake):
    response = client.put("/v2/read", headers=HEADERS)

    assert response.json() == []
    assert len(fake.statements) == 1
    fake.con_mgr.notify_read_all.assert_not_awaited()


def test_requires_the_user_header(fake):
    assert client.put("/v2/read").status_code == 400
