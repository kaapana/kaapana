import io
import tarfile

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.backends.base import StorageBackend


class _FakeBackend(StorageBackend):
    store_type = "s3"

    def fetch(self, coordinate, access_token):
        # Echo a single canned file; no network. Surface the token so we can
        # assert it was forwarded if needed.
        yield "model.bin", b"weights"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.get_backend",
        lambda store_type: _FakeBackend() if store_type in ("s3", "pacs") else None,
    )
    return TestClient(app)


def test_health(client) -> None:
    assert client.get("/v1/health").json() == {"status": "ok"}


def test_download_tar_groups_files_by_item_id(client) -> None:
    body = {
        "items": [
            {
                "id": "entity-1",
                "coordinates": [{"type": "s3", "bucket": "b", "key": "k/model.bin"}],
            }
        ],
        "format": "tar",
    }
    resp = client.post("/v1/download", json=body)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/x-tar")
    with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r") as tar:
        assert tar.getnames() == ["entity-1/model.bin"]
        assert tar.extractfile("entity-1/model.bin").read() == b"weights"


def test_download_forwards_access_token(monkeypatch) -> None:
    captured: dict = {}

    class _CaptureBackend(StorageBackend):
        store_type = "s3"

        def fetch(self, coordinate, access_token):
            captured["token"] = access_token
            yield "f.bin", b"x"

    monkeypatch.setattr("app.api.v1.get_backend", lambda store_type: _CaptureBackend())
    client = TestClient(app)
    body = {
        "items": [
            {"id": "e", "coordinates": [{"type": "s3", "bucket": "b", "key": "k"}]}
        ]
    }

    resp = client.post(
        "/v1/download", json=body, headers={"x-forwarded-access-token": "tok-1"}
    )
    assert resp.status_code == 200 and resp.content
    assert captured["token"] == "tok-1"

    resp = client.post(
        "/v1/download", json=body, headers={"Authorization": "Bearer tok-2"}
    )
    assert resp.status_code == 200 and resp.content
    assert captured["token"] == "tok-2"


def test_download_rejects_unsupported_coordinate_type(client, monkeypatch) -> None:
    monkeypatch.setattr("app.api.v1.get_backend", lambda store_type: None)
    body = {
        "items": [{"id": "e", "coordinates": [{"type": "url", "url": "http://x/y"}]}],
        "format": "tar",
    }
    resp = client.post("/v1/download", json=body)
    assert resp.status_code == 400
