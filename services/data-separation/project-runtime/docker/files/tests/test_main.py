"""Tests for the project-runtime filesystem endpoints.

project-runtime is the only component that mounts the project-namespace
``workflow-data-pv-claim`` PVC, so it exposes the delete/usage operations that
workflow-api delegates to during run-data cleanup. These tests sandbox the
mount root at a tmp_path and exercise the contract workflow-api relies on.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    monkeypatch.setattr(main, "WORKFLOW_DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def client(root) -> TestClient:
    return TestClient(main.app)


def _seed(root: Path, sub_path: str, files: dict[str, bytes]) -> Path:
    target = root / sub_path
    target.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = target / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    return target


# ---- usage ----------------------------------------------------------------


def test_usage_missing_path(client):
    resp = client.post("/filesystem/usage", json={"sub_path": "run-x"})
    assert resp.status_code == 200
    assert resp.json() == {"exists": False, "empty": True, "size_bytes": 0}


def test_usage_reports_size_and_non_empty(client, root):
    _seed(root, "run-1", {"a/b.dcm": b"x" * 100, "c.bin": b"y" * 23})
    resp = client.post("/filesystem/usage", json={"sub_path": "run-1"})
    assert resp.status_code == 200
    assert resp.json() == {"exists": True, "empty": False, "size_bytes": 123}


def test_usage_empty_dir(client, root):
    (root / "run-empty").mkdir()
    resp = client.post("/filesystem/usage", json={"sub_path": "run-empty"})
    assert resp.json() == {"exists": True, "empty": True, "size_bytes": 0}


# ---- delete ---------------------------------------------------------------


def test_delete_existing_is_recursive(client, root):
    target = _seed(root, "run-2", {"deep/nested/file.dcm": b"z" * 10})
    resp = client.post("/filesystem/delete", json={"sub_path": "run-2"})
    assert resp.status_code == 200
    assert resp.json() == {"deleted": True}
    assert not target.exists()


def test_delete_missing_is_idempotent_noop(client):
    resp = client.post("/filesystem/delete", json={"sub_path": "never-existed"})
    assert resp.status_code == 200
    assert resp.json() == {"deleted": False}


def test_delete_does_not_touch_siblings(client, root):
    a = _seed(root, "run-a", {"f": b"1"})
    b = _seed(root, "run-b", {"f": b"2"})
    client.post("/filesystem/delete", json={"sub_path": "run-a"})
    assert not a.exists()
    assert b.exists()


def test_delete_refuses_volume_root(client):
    resp = client.post("/filesystem/delete", json={"sub_path": ""})
    assert resp.status_code == 400
    assert "root" in resp.json()["detail"].lower()


# ---- guards ---------------------------------------------------------------


@pytest.mark.parametrize("endpoint", ["/filesystem/delete", "/filesystem/usage"])
@pytest.mark.parametrize("bad", ["../escape", "a/../../etc", "/etc/passwd"])
def test_path_traversal_rejected(client, endpoint, bad):
    resp = client.post(endpoint, json={"sub_path": bad})
    assert resp.status_code == 422  # blocked by the sub_path validator


@pytest.mark.parametrize("endpoint", ["/filesystem/delete", "/filesystem/usage"])
def test_unsupported_claim_name_rejected(client, endpoint):
    resp = client.post(
        endpoint, json={"sub_path": "run-1", "claim_name": "some-other-pvc"}
    )
    assert resp.status_code == 400
