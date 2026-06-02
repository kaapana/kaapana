"""Tests for the highest-bug-density parse paths in the store backends.

These exercise the WADO multipart parse (PACS) and the STS XML credential parse
(S3) against canned responses. They require the heavy store deps, so they are
skipped automatically in the bare venv and run in the container/CI image.
"""

import io

import pytest


def test_s3_sts_xml_parse_and_client_wiring(monkeypatch) -> None:
    pytest.importorskip("minio")
    pytest.importorskip("requests")
    import requests

    from app.services.backends import s3

    xml = (
        '<?xml version="1.0"?>'
        "<AssumeRoleWithWebIdentityResponse "
        'xmlns="https://sts.amazonaws.com/doc/2011-06-15/">'
        "<AssumeRoleWithWebIdentityResult><Credentials>"
        "<AccessKeyId>AK</AccessKeyId>"
        "<SecretAccessKey>SK</SecretAccessKey>"
        "<SessionToken>ST</SessionToken>"
        "<Expiration>2030-01-01T00:00:00Z</Expiration>"
        "</Credentials></AssumeRoleWithWebIdentityResult>"
        "</AssumeRoleWithWebIdentityResponse>"
    )

    class _Resp:
        text = xml

        def raise_for_status(self):
            pass

    captured: dict = {}

    def _fake_post(url, timeout=None):
        captured["url"] = url
        return _Resp()

    monkeypatch.setattr(requests, "post", _fake_post)

    minio_args: dict = {}

    class _FakeMinio:
        def __init__(self, endpoint, access_key, secret_key, session_token, secure):
            minio_args.update(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                session_token=session_token,
                secure=secure,
            )

    monkeypatch.setattr("minio.Minio", _FakeMinio)

    s3._minio_client("web-token", "minio-service.services.svc:9000")

    assert "WebIdentityToken=web-token" in captured["url"]
    assert minio_args["access_key"] == "AK"
    assert minio_args["secret_key"] == "SK"
    assert minio_args["session_token"] == "ST"


def test_pacs_multipart_parse_yields_named_instances(monkeypatch) -> None:
    pydicom = pytest.importorskip("pydicom")
    pytest.importorskip("requests_toolbelt")
    pytest.importorskip("requests")
    import requests
    from requests.structures import CaseInsensitiveDict

    from app.models import PacsCoordinate
    from app.services.backends import pacs

    # Build one minimal, valid DICOM instance.
    ds = pydicom.dataset.Dataset()
    ds.SOPInstanceUID = "1.2.3.4"
    ds.PatientID = "X"
    file_meta = pydicom.dataset.FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = "1.2.3.4"
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    fds = pydicom.dataset.FileDataset(
        "x.dcm", ds, file_meta=file_meta, preamble=b"\x00" * 128
    )
    buf = io.BytesIO()
    fds.save_as(buf, write_like_original=False)
    dicom_bytes = buf.getvalue()

    boundary = "BOUNDARY"
    body = (
        f"--{boundary}\r\nContent-Type: application/dicom\r\n\r\n".encode()
        + dicom_bytes
        + f"\r\n--{boundary}--\r\n".encode()
    )

    class _Resp:
        headers = CaseInsensitiveDict(
            {"Content-Type": f"multipart/related; boundary={boundary}"}
        )
        content = body

        def raise_for_status(self):
            pass

    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp())

    coord = PacsCoordinate(pacs_id="http://pacs", study_uid="s", series_uid="se")
    out = list(pacs.PacsBackend().fetch(coord, "tok"))

    assert len(out) == 1
    name, content = out[0]
    assert name == "1.2.3.4.dcm"
    assert content == dicom_bytes


class _FakeMinio:
    """Minimal in-memory MinIO stand-in: put/list/get of objects by key."""

    def __init__(self):
        self.objects: dict = {}

    def put_object(self, bucket, key, data, length):
        self.objects[key] = data.read()

    def list_objects(self, bucket, prefix="", recursive=False):
        class _Obj:
            def __init__(self, name):
                self.object_name = name

        return [_Obj(k) for k in sorted(self.objects) if k.startswith(prefix)]

    def get_object(self, bucket, key):
        payload = self.objects[key]

        class _Resp:
            def read(self_inner):
                return payload

            def close(self_inner):
                pass

            def release_conn(self_inner):
                pass

        return _Resp()


def test_s3_fetch_single_object_yields_basename(monkeypatch):
    pytest.importorskip("minio")

    from app.models import S3Coordinate
    from app.services.backends import s3

    client = _FakeMinio()
    client.objects = {"single/report.txt": b"hello"}
    monkeypatch.setattr(s3, "_minio_client", lambda token, endpoint: client)

    coord = S3Coordinate(bucket="proj", key="single/report.txt")
    out = list(s3.S3Backend().fetch(coord, "tok"))

    assert out == [("report.txt", b"hello")]


def test_s3_store_folder_preserves_structure_and_returns_one_prefix_coord(monkeypatch):
    pytest.importorskip("minio")

    from app.models import S3UploadTarget
    from app.services.backends import s3

    client = _FakeMinio()
    monkeypatch.setattr(s3, "_minio_client", lambda token, endpoint: client)

    # Default unit == "folder"; a file in a sub-directory must keep its relpath.
    target = S3UploadTarget(bucket="proj", key_prefix="models/run-1")
    coords = s3.S3Backend().store(
        target,
        [("model.bin", b"weights"), ("weights/layer1.bin", b"L1")],
        "tok",
    )

    assert client.objects == {
        "models/run-1/model.bin": b"weights",
        "models/run-1/weights/layer1.bin": b"L1",
    }
    # One folder coordinate addressing the whole prefix.
    assert len(coords) == 1
    assert coords[0].bucket == "proj"
    assert coords[0].key == "models/run-1/"
    assert coords[0].is_prefix is True
    assert coords[0].type == "s3"


def test_s3_store_file_unit_returns_single_object_coord(monkeypatch):
    pytest.importorskip("minio")

    from app.models import S3UploadTarget
    from app.services.backends import s3

    client = _FakeMinio()
    monkeypatch.setattr(s3, "_minio_client", lambda token, endpoint: client)

    target = S3UploadTarget(bucket="proj", key_prefix="single/", unit="file")
    coords = s3.S3Backend().store(target, [("report.txt", b"hello")], "tok")

    assert client.objects == {"single/report.txt": b"hello"}
    assert len(coords) == 1
    assert coords[0].key == "single/report.txt"
    assert coords[0].is_prefix is False


def test_s3_store_file_unit_rejects_multiple_files(monkeypatch):
    pytest.importorskip("minio")

    from app.models import S3UploadTarget
    from app.services.backends import s3

    monkeypatch.setattr(s3, "_minio_client", lambda token, endpoint: _FakeMinio())
    target = S3UploadTarget(bucket="proj", unit="file")
    with pytest.raises(ValueError, match="exactly one file"):
        s3.S3Backend().store(target, [("a", b"1"), ("b", b"2")], "tok")


def test_s3_store_folder_rejects_empty_prefix(monkeypatch):
    pytest.importorskip("minio")

    from app.models import S3UploadTarget
    from app.services.backends import s3

    monkeypatch.setattr(s3, "_minio_client", lambda token, endpoint: _FakeMinio())
    # A folder coordinate over an empty prefix would list the whole bucket on fetch.
    target = S3UploadTarget(bucket="proj", key_prefix="", unit="folder")
    with pytest.raises(ValueError, match="non-empty key_prefix"):
        s3.S3Backend().store(target, [("a", b"1")], "tok")


def test_s3_store_requires_access_token() -> None:
    pytest.importorskip("minio")
    from app.models import S3UploadTarget
    from app.services.backends import s3

    with pytest.raises(ValueError):
        s3.S3Backend().store(S3UploadTarget(bucket="b"), [("f", b"x")], None)


def test_pacs_store_stows_multipart_and_returns_one_coord_per_series(monkeypatch):
    pydicom = pytest.importorskip("pydicom")
    pytest.importorskip("requests")
    import requests

    from app.models import PacsUploadTarget
    from app.services.backends import pacs

    def _dicom(study: str, series: str, sop: str) -> bytes:
        ds = pydicom.dataset.Dataset()
        ds.SOPInstanceUID = sop
        ds.StudyInstanceUID = study
        ds.SeriesInstanceUID = series
        file_meta = pydicom.dataset.FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = pydicom.uid.SecondaryCaptureImageStorage
        file_meta.MediaStorageSOPInstanceUID = sop
        file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
        fds = pydicom.dataset.FileDataset(
            "x.dcm", ds, file_meta=file_meta, preamble=b"\x00" * 128
        )
        buf = io.BytesIO()
        fds.save_as(buf, write_like_original=False)
        return buf.getvalue()

    captured: dict = {}

    class _Resp:
        def raise_for_status(self):
            pass

    def _fake_post(url, data=None, headers=None, timeout=None):
        captured.update(url=url, data=data, headers=headers)
        return _Resp()

    monkeypatch.setattr(requests, "post", _fake_post)

    # Two instances of the same series + one of another series.
    a = _dicom("study-1", "series-1", "1.1")
    b = _dicom("study-1", "series-1", "1.2")
    c = _dicom("study-1", "series-2", "2.1")

    coords = pacs.PacsBackend().store(
        PacsUploadTarget(pacs_id="http://pacs"),
        [("a.dcm", a), ("b.dcm", b), ("c.dcm", c)],
        "tok",
    )

    assert captured["url"] == "http://pacs/studies"
    assert 'type="application/dicom"' in captured["headers"]["Content-Type"]
    assert captured["headers"]["Authorization"] == "Bearer tok"
    # All three instances are in the STOW body.
    assert captured["data"].count(b"application/dicom") == 3
    # One coordinate per distinct series, study/series UIDs preserved.
    assert [(c.study_uid, c.series_uid) for c in coords] == [
        ("study-1", "series-1"),
        ("study-1", "series-2"),
    ]
    assert all(c.pacs_id == "http://pacs" and c.type == "pacs" for c in coords)


def test_s3_fetch_prefix_yields_structure_preserving_relpaths(monkeypatch):
    pytest.importorskip("minio")

    from app.models import S3Coordinate
    from app.services.backends import s3

    client = _FakeMinio()
    client.objects = {
        "models/run-1/model.bin": b"weights",
        "models/run-1/weights/layer1.bin": b"L1",
        "models/run-1/sub/": b"",  # directory marker -> skipped
    }
    monkeypatch.setattr(s3, "_minio_client", lambda token, endpoint: client)

    coord = S3Coordinate(bucket="proj", key="models/run-1/", is_prefix=True)
    out = dict(s3.S3Backend().fetch(coord, "tok"))

    assert out == {"model.bin": b"weights", "weights/layer1.bin": b"L1"}


def test_folder_coordinate_materialises_nested_structure_under_entity(
    monkeypatch, tmp_path
):
    """End-to-end wiring: a folder coordinate's nested objects survive the
    fetch -> entity-prefixed arcname -> stream_tar -> extract round-trip.

    Unlike PACS (flat instance names), an S3 folder yields sub-directory relpaths;
    this asserts the nested dirs land under ``<entity_id>/`` on extraction.
    """
    import io
    import tarfile

    pytest.importorskip("minio")

    from app.models import S3Coordinate
    from app.services.archive import stream_tar
    from app.services.backends import s3

    client = _FakeMinio()
    client.objects = {
        "models/run-1/model.bin": b"weights",
        "models/run-1/weights/layer1.bin": b"L1",
    }
    monkeypatch.setattr(s3, "_minio_client", lambda token, endpoint: client)

    coord = S3Coordinate(bucket="proj", key="models/run-1/", is_prefix=True)
    # Mirror api/v1._iter_files: prefix each relpath with the entity id.
    files = (
        (f"e1/{relpath}", content)
        for relpath, content in s3.S3Backend().fetch(coord, "tok")
    )
    archive = b"".join(stream_tar(files))

    with tarfile.open(fileobj=io.BytesIO(archive), mode="r") as tar:
        tar.extractall(path=tmp_path, filter="data")

    assert (tmp_path / "e1" / "model.bin").read_bytes() == b"weights"
    assert (tmp_path / "e1" / "weights" / "layer1.bin").read_bytes() == b"L1"
