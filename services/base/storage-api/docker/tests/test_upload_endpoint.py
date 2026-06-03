import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import S3Coordinate
from app.services.backends.base import StorageBackend


class _FakeS3Backend(StorageBackend):
    store_type = "s3"

    def __init__(self):
        self.captured = {}

    def store(self, target, files, access_token):
        materialised = [(name, bytes(content)) for name, content in files]
        self.captured = {
            "target": target,
            "token": access_token,
            "files": materialised,
        }
        prefix = target.key_prefix or ""
        return [
            S3Coordinate(bucket=target.bucket, key=f"{prefix}{name}")
            for name, _ in materialised
        ]


def _descriptor(**kw) -> dict:
    return {"descriptor": json.dumps(kw)}


def test_upload_writes_files_and_returns_coordinates(monkeypatch) -> None:
    backend = _FakeS3Backend()
    monkeypatch.setattr("app.api.v1.get_backend", lambda store_type: backend)
    client = TestClient(app)

    resp = client.post(
        "/v1/upload",
        data=_descriptor(store="s3", bucket="proj", key_prefix="models/run-1/"),
        files=[("files", ("model.bin", b"weights", "application/octet-stream"))],
        headers={"x-forwarded-access-token": "tok-1"},
    )

    assert resp.status_code == 200
    assert resp.json() == {
        "coordinates": [
            {
                "type": "s3",
                "bucket": "proj",
                "key": "models/run-1/model.bin",
                "region": None,
                "endpoint_url": None,
                "is_prefix": False,
            }
        ]
    }
    assert backend.captured["token"] == "tok-1"
    assert backend.captured["files"] == [("model.bin", b"weights")]
    assert backend.captured["target"].bucket == "proj"


def test_upload_forwards_unit_to_backend(monkeypatch) -> None:
    backend = _FakeS3Backend()
    monkeypatch.setattr("app.api.v1.get_backend", lambda store_type: backend)
    client = TestClient(app)

    resp = client.post(
        "/v1/upload",
        data=_descriptor(store="s3", bucket="proj", key_prefix="p/", unit="file"),
        files=[("files", ("report.txt", b"x", "application/octet-stream"))],
        headers={"x-forwarded-access-token": "tok"},
    )

    assert resp.status_code == 200
    assert backend.captured["target"].unit == "file"


def test_upload_forwards_bearer_token(monkeypatch) -> None:
    backend = _FakeS3Backend()
    monkeypatch.setattr("app.api.v1.get_backend", lambda store_type: backend)
    client = TestClient(app)

    resp = client.post(
        "/v1/upload",
        data=_descriptor(store="s3", bucket="b"),
        files=[("files", ("f.bin", b"x"))],
        headers={"Authorization": "Bearer tok-2"},
    )
    assert resp.status_code == 200
    assert backend.captured["token"] == "tok-2"


def test_upload_maps_storage_error_to_its_status(monkeypatch) -> None:
    # A backend StorageError (e.g. MinIO AccessDenied -> 403) must surface as
    # that 4xx, not as FastAPI's default 500.
    from app.services.backends.base import StorageError

    class _DenyingBackend(StorageBackend):
        store_type = "s3"

        def store(self, target, files, access_token):
            raise StorageError(403, "Access Denied.")

    monkeypatch.setattr("app.api.v1.get_backend", lambda store_type: _DenyingBackend())
    client = TestClient(app)
    resp = client.post(
        "/v1/upload",
        data=_descriptor(store="s3", bucket="b"),
        files=[("files", ("f.bin", b"x"))],
        headers={"x-forwarded-access-token": "tok"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Access Denied."


def test_upload_rejects_unsupported_store(monkeypatch) -> None:
    monkeypatch.setattr("app.api.v1.get_backend", lambda store_type: None)
    client = TestClient(app)
    resp = client.post(
        "/v1/upload",
        data=_descriptor(store="s3", bucket="b"),
        files=[("files", ("f.bin", b"x"))],
    )
    assert resp.status_code == 400


def test_upload_rejects_invalid_descriptor() -> None:
    client = TestClient(app)
    # Unknown store discriminator -> validation error -> 422.
    resp = client.post(
        "/v1/upload",
        data=_descriptor(store="floppy", path="/dev/null"),
        files=[("files", ("f.bin", b"x"))],
    )
    assert resp.status_code == 422

    # Not even JSON.
    resp = client.post(
        "/v1/upload",
        data={"descriptor": "not-json"},
        files=[("files", ("f.bin", b"x"))],
    )
    assert resp.status_code == 422
