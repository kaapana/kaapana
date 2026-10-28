"""Tests for kaapana_nnunet.store against a real S3 server (Kaapana's minio image).

    docker run -d --rm -p 127.0.0.1:19000:9000 -e MINIO_ROOT_USER=testadmin \
        -e MINIO_ROOT_PASSWORD=testadmin123 <registry>/minio:<version> server /data
    NNUNET_TEST_S3=127.0.0.1:19000 pytest tests/
"""

import os
import threading
from datetime import timedelta
from io import BytesIO

import blosc2
import numpy as np
import pytest
from kaapana_nnunet.store import AlreadyPublished, IntegrityError, NotPublished, S3Store, StoreError

ENDPOINT = os.environ.get("NNUNET_TEST_S3")
pytestmark = pytest.mark.skipif(not ENDPOINT, reason="set NNUNET_TEST_S3=host:port of a test S3 server")


def make_tree(root, files):
    for rel, data in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def remote_keys(store, prefix=""):
    return sorted(o.object_name for o in store._client().list_objects(store.bucket, prefix=prefix, recursive=True))


TREE = {
    "dataset.json": b'{"name": "x"}',
    "imagesTr/case_000_0000.nii.gz": os.urandom(1000),
    "imagesTr/case_000_0001.nii.gz": os.urandom(2000),
    "labelsTr/case_000.nii.gz": os.urandom(500),
}


def test_roundtrip(store, tmp_path):
    make_tree(tmp_path / "src", TREE)
    marker = store.publish(tmp_path / "src", "raw/Dataset001_X", meta={"k": 1})

    assert {e["path"] for e in marker["files"]} == set(TREE)
    assert store.read_marker("raw/Dataset001_X")["meta"] == {"k": 1}
    assert not remote_keys(store, "nnunet/.staging/")

    store.fetch("raw/Dataset001_X", tmp_path / "dst")
    for rel, data in TREE.items():
        assert (tmp_path / "dst" / rel).read_bytes() == data
    assert not list((tmp_path / "dst").rglob(".*.part-*"))


def test_include_filter(store, tmp_path):
    make_tree(tmp_path / "src", TREE)
    store.publish(tmp_path / "src", "raw/D")
    store.fetch("raw/D", tmp_path / "dst", include=lambda p: p.startswith("labelsTr/"))
    assert [p.relative_to(tmp_path / "dst").as_posix() for p in (tmp_path / "dst").rglob("*") if p.is_file()] == [
        "labelsTr/case_000.nii.gz"
    ]


def test_not_published(store, tmp_path):
    with pytest.raises(NotPublished):
        store.fetch("raw/missing", tmp_path)


def test_failed_upload_leaves_nothing_visible(store, tmp_path, monkeypatch):
    make_tree(tmp_path / "src", TREE)
    real = store._client()
    calls = {"n": 0}
    original = real.fput_object

    def flaky(bucket, key, path, *a, **kw):
        calls["n"] += 1
        if calls["n"] == 3:
            raise OSError("pod killed")
        return original(bucket, key, path, *a, **kw)

    monkeypatch.setattr(real, "fput_object", flaky)
    monkeypatch.setattr("kaapana_nnunet.store.time.sleep", lambda s: None)
    # OSError is retried; make every retry fail too
    monkeypatch.setattr("kaapana_nnunet.store._retry", lambda fn, **kw: fn())
    with pytest.raises(OSError):
        store.publish(tmp_path / "src", "raw/D")

    assert not store.is_published("raw/D")
    assert remote_keys(store) == []  # neither final files nor staging leftovers


def test_failed_move_has_no_marker(store, tmp_path, monkeypatch):
    make_tree(tmp_path / "src", TREE)
    real = store._client()
    original = real.copy_object
    calls = {"n": 0}

    def flaky(*a, **kw):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("network gone")
        return original(*a, **kw)

    monkeypatch.setattr(real, "copy_object", flaky)
    monkeypatch.setattr("kaapana_nnunet.store._retry", lambda fn, **kw: fn())
    store.workers = 1
    with pytest.raises(OSError):
        store.publish(tmp_path / "src", "raw/D")

    assert not store.is_published("raw/D")
    assert not remote_keys(store, "nnunet/.staging/")
    with pytest.raises(NotPublished):
        store.fetch("raw/D", tmp_path / "dst")

    # a rerun publishes cleanly over the partial copy
    monkeypatch.undo()
    store.publish(tmp_path / "src", "raw/D")
    store.fetch("raw/D", tmp_path / "dst")
    assert (tmp_path / "dst" / "dataset.json").read_bytes() == TREE["dataset.json"]


def test_no_silent_overwrite(store, tmp_path):
    make_tree(tmp_path / "src", TREE)
    store.publish(tmp_path / "src", "raw/D")
    with pytest.raises(AlreadyPublished):
        store.publish(tmp_path / "src", "raw/D")

    (tmp_path / "src" / "dataset.json").write_bytes(b"new")
    first = store.read_marker("raw/D")["id"]
    store.publish(tmp_path / "src", "raw/D", overwrite=True)
    assert store.read_marker("raw/D")["id"] != first
    store.fetch("raw/D", tmp_path / "dst")
    assert (tmp_path / "dst" / "dataset.json").read_bytes() == b"new"


@pytest.mark.parametrize("same_size", [False, True])
def test_corrupted_object_is_detected(store, tmp_path, same_size):
    make_tree(tmp_path / "src", TREE)
    store.publish(tmp_path / "src", "raw/D")
    good = TREE["labelsTr/case_000.nii.gz"]
    bad = bytes([good[0] ^ 1]) + good[1:] if same_size else b"garbage"
    store._client().put_object(store.bucket, "nnunet/raw/D/labelsTr/case_000.nii.gz", BytesIO(bad), len(bad))

    with pytest.raises(IntegrityError):
        store.fetch("raw/D", tmp_path / "dst")
    assert not (tmp_path / "dst" / "labelsTr" / "case_000.nii.gz").exists()
    assert not list((tmp_path / "dst").rglob(".*.part-*"))


def test_republish_during_fetch_is_detected(store, tmp_path, monkeypatch):
    make_tree(tmp_path / "src", TREE)
    store.publish(tmp_path / "src", "raw/D")
    real_read = store.read_marker
    reads = {"n": 0}

    def read_then_republish(prefix, unit=None):
        marker = real_read(prefix, unit)
        reads["n"] += 1
        if reads["n"] == 1:
            # same content, new publish id: a concurrent republish
            store.publish(tmp_path / "src", "raw/D", overwrite=True)
        return marker

    monkeypatch.setattr(store, "read_marker", read_then_republish)
    with pytest.raises(IntegrityError, match="republished"):
        store.fetch("raw/D", tmp_path / "dst")


def test_resume_keeps_valid_files_and_replaces_wrong_ones(store, tmp_path, monkeypatch):
    make_tree(tmp_path / "src", TREE)
    store.publish(tmp_path / "src", "raw/D")
    store.fetch("raw/D", tmp_path / "dst")
    (tmp_path / "dst" / "dataset.json").write_bytes(b"locally broken")

    downloaded = []
    real = store._client()
    original = real.fget_object
    monkeypatch.setattr(real, "fget_object", lambda b, k, p, *a, **kw: (downloaded.append(k), original(b, k, p))[1])
    store.fetch("raw/D", tmp_path / "dst")
    assert downloaded == ["nnunet/raw/D/dataset.json"]
    assert (tmp_path / "dst" / "dataset.json").read_bytes() == TREE["dataset.json"]


def test_concurrent_reader_sees_nothing_or_everything(store, tmp_path):
    files = {f"data/case_{i:03d}.b2nd": os.urandom(50_000) for i in range(40)}
    make_tree(tmp_path / "src", files)
    stop = threading.Event()
    outcomes = []

    def reader():
        n = 0
        while not stop.is_set():
            n += 1
            dst = tmp_path / f"reader{n}"
            try:
                store.fetch("preprocessed/D", dst, unit="data")
                got = {p.relative_to(dst).as_posix(): p.read_bytes() for p in dst.rglob("*") if p.is_file()}
                assert got == files
                outcomes.append("complete")
            except NotPublished:
                outcomes.append("absent")

    t = threading.Thread(target=reader)
    t.start()
    store.publish(tmp_path / "src", "preprocessed/D", unit="data")
    stop.set()
    t.join()
    store.fetch("preprocessed/D", tmp_path / "final", unit="data")
    assert set(outcomes) <= {"absent", "complete"}
    assert "absent" in outcomes


def test_units_share_a_prefix(store, tmp_path):
    make_tree(
        tmp_path / "src",
        {
            "dataset.json": b"d",
            "dataset_fingerprint.json": b"f",
            "PlansA.json": b"a",
            "PlansA_3d_fullres/c0.b2nd": b"x" * 10,
            "PlansA_2d/c0.b2nd": b"y" * 10,
        },
    )
    p = "preprocessed/Dataset001_X"
    store.publish(tmp_path / "src", p, ["dataset.json", "dataset_fingerprint.json"], unit="fingerprint")
    store.publish(tmp_path / "src", p, ["dataset.json", "PlansA.json"], unit="plans.PlansA")
    store.publish(tmp_path / "src", p, ["PlansA_3d_fullres"], unit="data.PlansA_3d_fullres")
    store.publish(tmp_path / "src", p, ["PlansA_2d"], unit="data.PlansA_2d")

    assert sorted(m["unit"] for m in store.list_markers("preprocessed")) == [
        "data.PlansA_2d",
        "data.PlansA_3d_fullres",
        "fingerprint",
        "plans.PlansA",
    ]

    store.delete(p, unit="plans.PlansA")
    keys = remote_keys(store, f"nnunet/{p}/")
    assert f"nnunet/{p}/PlansA.json" not in keys
    assert f"nnunet/{p}/dataset.json" in keys  # still used by the fingerprint unit
    store.fetch(p, tmp_path / "dst", unit="fingerprint")


def test_invalid_names(store, tmp_path):
    with pytest.raises(StoreError):
        S3Store.marker_name("../x")
    make_tree(tmp_path / "src", {"a": b"1"})
    with pytest.raises(StoreError):
        store.publish(tmp_path / "src", "raw/D", ["../src/a"])
    with pytest.raises(StoreError):
        store.publish(tmp_path / "src", "raw/D", ["missing"])


def test_cleanup_staging(store, tmp_path):
    data = b"leftover"
    store._client().put_object(store.bucket, "nnunet/.staging/dead/x", BytesIO(data), len(data))
    store.cleanup_staging()
    assert remote_keys(store, "nnunet/.staging/") == ["nnunet/.staging/dead/x"]
    store.cleanup_staging(older_than=timedelta(seconds=-60))
    assert remote_keys(store, "nnunet/.staging/") == []


def test_blosc2_preprocessed_roundtrip(store, tmp_path):
    """nnU-Net trains on mmap'ed .b2nd files with partial decompression: after fetch,
    random slices must decode identically to the source, and multipart objects must survive."""
    rng = np.random.default_rng(0)
    src = tmp_path / "src" / "nnUNetPlans_3d_fullres"
    src.mkdir(parents=True)
    arrays = {}
    for i, shape in enumerate([(1, 64, 128, 128), (2, 160, 192, 192)]):
        data = rng.normal(size=shape).astype(np.float32)
        seg = rng.integers(0, 3, size=(1,) + shape[1:], dtype=np.int8)
        cparams = {"codec": blosc2.Codec.ZSTD, "clevel": 8}
        blosc2.asarray(
            np.ascontiguousarray(data),
            urlpath=str(src / f"case_{i}.b2nd"),
            chunks=(1, 32, 64, 64),
            blocks=(1, 16, 32, 32),
            cparams=cparams,
            mmap_mode="w+",
        )
        blosc2.asarray(
            np.ascontiguousarray(seg),
            urlpath=str(src / f"case_{i}_seg.b2nd"),
            chunks=(1, 32, 64, 64),
            blocks=(1, 16, 32, 32),
            cparams=cparams,
            mmap_mode="w+",
        )
        arrays[i] = (data, seg)
    # the 2-channel case is well above the 5 MiB multipart threshold
    assert (src / "case_1.b2nd").stat().st_size > 16 * 1024 * 1024

    store.publish(tmp_path / "src", "preprocessed/D", ["nnUNetPlans_3d_fullres"], unit="data.nnUNetPlans_3d_fullres")
    dst = tmp_path / "dst"
    store.fetch("preprocessed/D", dst, unit="data.nnUNetPlans_3d_fullres")

    for i, (data, seg) in arrays.items():
        d = blosc2.open(str(dst / "nnUNetPlans_3d_fullres" / f"case_{i}.b2nd"), mode="r", mmap_mode="r")
        s = blosc2.open(str(dst / "nnUNetPlans_3d_fullres" / f"case_{i}_seg.b2nd"), mode="r", mmap_mode="r")
        assert d.shape == data.shape and s.shape == seg.shape
        for _ in range(10):
            z, y, x = (int(rng.integers(0, n - 20)) for n in data.shape[1:])
            sl = (slice(None), slice(z, z + 20), slice(y, y + 20), slice(x, x + 20))
            np.testing.assert_array_equal(d[sl], data[sl])
            np.testing.assert_array_equal(s[sl], seg[sl])


def test_adopt_manual_upload(store, tmp_path):
    client = store._client()
    for rel, data in TREE.items():
        client.put_object(store.bucket, f"nnunet/raw/Dataset009_Up/{rel}", BytesIO(data), len(data))
    client.put_object(store.bucket, "nnunet/raw/Dataset009_Up/.reserved", BytesIO(b""), 0)
    assert not store.is_published("raw/Dataset009_Up")

    marker = store.adopt("raw/Dataset009_Up", meta={"source": "upload"})
    assert {e["path"] for e in marker["files"]} == set(TREE)
    store.fetch("raw/Dataset009_Up", tmp_path / "dst")
    for rel, data in TREE.items():
        assert (tmp_path / "dst" / rel).read_bytes() == data


def test_adopt_refuses_changing_upload(store, monkeypatch):
    client = store._client()
    client.put_object(store.bucket, "nnunet/raw/D/a", BytesIO(b"1"), 1)
    original = client.get_object

    def upload_continues(bucket, key, *a, **kw):
        client.put_object(store.bucket, "nnunet/raw/D/b", BytesIO(b"2"), 1)
        return original(bucket, key, *a, **kw)

    monkeypatch.setattr(client, "get_object", upload_continues)
    with pytest.raises(IntegrityError):
        store.adopt("raw/D")
    monkeypatch.undo()
    assert not store.is_published("raw/D")
