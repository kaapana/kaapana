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
    """Minimal in-memory MinIO stand-in: get of objects by key."""

    def __init__(self):
        self.objects: dict = {}

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
