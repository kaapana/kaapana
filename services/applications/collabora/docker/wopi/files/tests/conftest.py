import datetime
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
from minio.datatypes import Object
from minio.error import S3Error

os.environ.setdefault("COLLABORA_URL", "http://collabora.test/collabora")
os.environ.setdefault("WOPI_API_ENDPOINT", "wopi.test:5000")
os.environ.setdefault("MINIO_URL", "minio.test:9000")
os.environ.setdefault("AII_URL", "http://aii.test:8080")
UI_DIRECTORY = Path(tempfile.mkdtemp())
(UI_DIRECTORY / "index.html").write_text("<!doctype html><title>Documents</title>")
os.environ["UI_DIRECTORY"] = str(UI_DIRECTORY)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import main  # noqa: E402
from app.dependencies import get_minio_client, get_wopi  # noqa: E402
from app.model.wopi import WOPIAction, WOPIApp  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

PROJECT = {"id": "2f0c5a1e-0000-0000-0000-000000000000", "short_id": "2f0c5a1e", "s3_bucket": "project-2f0c5a1e"}
OTHER_BUCKET = "project-other"


class FakeResponse:
    def __init__(self, data: bytes, etag: str):
        self.data = data
        self.headers = {"ETag": f'"{etag}"'}
        self.closed = False
        self.released = False

    def stream(self, amt):
        for start in range(0, len(self.data), amt):
            yield self.data[start : start + amt]

    def close(self):
        self.closed = True

    def release_conn(self):
        self.released = True


class FakeMinio:
    def __init__(self):
        self.objects: dict[tuple[str, str], tuple[bytes, datetime.datetime]] = {}
        self.denied_buckets: set[str] = set()
        self.listed: list[str] = []
        self.responses: list[FakeResponse] = []
        self.clock = datetime.datetime(2026, 10, 1, 9, 0, tzinfo=datetime.timezone.utc)

    def add(self, bucket: str, path: str, data: bytes = b"data"):
        self.clock += datetime.timedelta(minutes=1)
        self.objects[(bucket, path)] = (data, self.clock)

    def _error(self, code, bucket, path=None):
        return S3Error(code, code, None, None, None, None, bucket, path)

    def _check(self, bucket):
        if bucket in self.denied_buckets:
            raise self._error("AccessDenied", bucket)

    def _object(self, bucket, path):
        data, modified = self.objects[(bucket, path)]
        return Object(bucket, path, last_modified=modified, etag=hashlib.md5(data).hexdigest(), size=len(data))

    def list_objects(self, bucket, recursive=False):
        self._check(bucket)
        self.listed.append(bucket)
        return [self._object(b, p) for (b, p) in self.objects if b == bucket]

    def stat_object(self, bucket, path):
        self._check(bucket)
        if (bucket, path) not in self.objects:
            raise self._error("NoSuchKey", bucket, path)
        return self._object(bucket, path)

    def get_object(self, bucket, path):
        obj = self.stat_object(bucket, path)
        response = FakeResponse(self.objects[(bucket, path)][0], obj.etag)
        self.responses.append(response)
        return response

    def put_object(self, bucket, path, data, length):
        self._check(bucket)
        self.add(bucket, path, data.read(length))


def collabora_apps():
    return [
        WOPIApp(
            "external-http",
            "http://collabora.test/writer.ico",
            "writer",
            [
                WOPIAction("odt", "view", "http://collabora.test/cool.html?"),
                WOPIAction("odt", "edit", "http://collabora.test/cool.html?"),
                WOPIAction("docx", "edit", "http://collabora.test/cool.html?"),
            ],
        ),
        WOPIApp("external-http", None, "calc", [WOPIAction("xlsx", "edit", "http://collabora.test/calc.html")]),
    ]


@pytest.fixture
def minio():
    return FakeMinio()


@pytest.fixture
def wopi_srv(monkeypatch):
    wopi_srv = get_wopi()
    monkeypatch.setattr(wopi_srv, "apps", collabora_apps())
    return wopi_srv


@pytest.fixture
def client(minio, wopi_srv, monkeypatch):
    async def no_discovery(_wopi_srv):
        return None

    monkeypatch.setattr(main, "wopi_discovery_task", no_discovery)
    main.app.dependency_overrides[get_minio_client] = lambda: minio
    with TestClient(main.app, headers={"Project": json.dumps(PROJECT), "Authorization": "Bearer token"}) as client:
        yield client
    main.app.dependency_overrides.clear()
