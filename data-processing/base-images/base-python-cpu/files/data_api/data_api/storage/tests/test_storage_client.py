"""Unit tests for StorageClient — async, no network (httpx.MockTransport).

A fake DataClient resolves coordinates and a MockTransport streams a small
in-memory tar, exercising the download orchestration + completeness check.
"""

import asyncio
import io
import json
import tarfile
from pathlib import Path

import httpx
import pytest

from data_api import StorageClient


class _FakeData:
    """Minimal stand-in for DataClient (awaitable get_entity + static coords)."""

    def __init__(self, coords_by_id):
        self._coords = coords_by_id

    async def get_entity(self, entity_id):
        return {"id": entity_id, "storage_coordinates": self._coords[entity_id]}

    @staticmethod
    def get_storage_coordinates(entity):
        return entity["storage_coordinates"]


def _make_tar(files: dict) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, content in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


async def test_download_entities_unpacks_and_groups_by_id(tmp_path):
    # One /v1/download request per entity now (bounded fan-out), each returning a
    # tar scoped to that entity. We verify each request carries a single item and
    # the union materialises under <entity_id>/.
    seen = []
    files_per_id = {"e1": ("e1/a.dcm", b"x"), "e2": ("e2/model.bin", b"y")}

    def handler(request):
        body = json.loads(request.content)
        assert len(body["items"]) == 1  # one entity per request
        item = body["items"][0]
        seen.append(item["id"])
        assert str(request.url).endswith("/v1/download")
        assert request.headers.get("x-forwarded-access-token") == "tok"
        name, content = files_per_id[item["id"]]
        return httpx.Response(200, content=_make_tar({name: content}))

    data = _FakeData(
        {
            "e1": [
                {"type": "pacs", "pacs_id": "p", "study_uid": "s", "series_uid": "se"}
            ],
            "e2": [{"type": "s3", "bucket": "b", "key": "k"}],
        }
    )
    async with StorageClient(
        base_url="http://storage-api.svc",
        access_token="tok",
        transport=httpx.MockTransport(handler),
    ) as storage:
        await storage.download_entities(["e1", "e2"], tmp_path, data_client=data)

    assert (tmp_path / "e1" / "a.dcm").read_bytes() == b"x"
    assert (tmp_path / "e2" / "model.bin").read_bytes() == b"y"
    assert set(seen) == {"e1", "e2"}


async def test_download_entities_bounds_concurrency(tmp_path, monkeypatch):
    # The semaphore must cap simultaneous downloads at max_concurrency while still
    # actually running them in parallel.
    ids = [f"e{i}" for i in range(20)]
    data = _FakeData({eid: [{"type": "s3", "bucket": "b", "key": eid}] for eid in ids})

    inflight = 0
    peak = 0
    lock = asyncio.Lock()

    async def fake_download(items, output, format="tar"):
        nonlocal inflight, peak
        async with lock:
            inflight += 1
            peak = max(peak, inflight)
        await asyncio.sleep(0.01)
        for item in items:  # materialise so the completeness check passes
            folder = Path(output) / item["id"]
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "f").write_bytes(b"x")
        async with lock:
            inflight -= 1
        return Path(output)

    async with StorageClient(
        base_url="http://s",
        transport=httpx.MockTransport(lambda r: httpx.Response(200)),
    ) as storage:
        monkeypatch.setattr(storage, "download", fake_download)
        await storage.download_entities(
            ids, tmp_path, data_client=data, max_concurrency=5
        )

    assert peak <= 5
    assert peak > 1  # proves the downloads actually overlapped


async def test_download_entities_fails_loud_on_incomplete(tmp_path):
    # e2's request yields an empty archive -> completeness check must raise.
    def handler(request):
        item = json.loads(request.content)["items"][0]
        if item["id"] == "e1":
            return httpx.Response(200, content=_make_tar({"e1/a.dcm": b"x"}))
        return httpx.Response(200, content=_make_tar({}))

    data = _FakeData(
        {
            "e1": [{"type": "s3", "bucket": "b", "key": "k"}],
            "e2": [{"type": "s3", "bucket": "b", "key": "k2"}],
        }
    )
    with pytest.raises(RuntimeError, match="Incomplete download"):
        async with StorageClient(
            base_url="http://s", transport=httpx.MockTransport(handler)
        ) as storage:
            await storage.download_entities(["e1", "e2"], tmp_path, data_client=data)


async def test_download_entities_noop_on_empty(tmp_path):
    def handler(request):  # pragma: no cover - must not be called
        raise AssertionError("storage-api should not be contacted for empty input")

    async with StorageClient(
        base_url="http://s", transport=httpx.MockTransport(handler)
    ) as storage:
        out = await storage.download_entities([], tmp_path, data_client=_FakeData({}))
    assert out == tmp_path


async def test_upload_posts_multipart_and_returns_coordinates():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["token"] = request.headers.get("x-forwarded-access-token")
        captured["content_type"] = request.headers.get("content-type", "")
        captured["body"] = request.content
        return httpx.Response(
            200,
            json={
                "coordinates": [
                    {"type": "s3", "bucket": "proj", "key": "models/run-1/model.bin"}
                ]
            },
        )

    async with StorageClient(
        base_url="http://storage-api.svc",
        access_token="tok",
        transport=httpx.MockTransport(handler),
    ) as storage:
        coords = await storage.upload(
            files=[("model.bin", b"weights")],
            store="s3",
            target={"bucket": "proj", "key_prefix": "models/run-1/"},
        )

    assert coords == [{"type": "s3", "bucket": "proj", "key": "models/run-1/model.bin"}]
    assert captured["url"].endswith("/v1/upload")
    assert captured["token"] == "tok"
    assert captured["content_type"].startswith("multipart/form-data")
    # Descriptor JSON merges the store discriminator with the target hints.
    assert b'"store": "s3"' in captured["body"]
    assert b'"bucket": "proj"' in captured["body"]
    assert b"weights" in captured["body"]
