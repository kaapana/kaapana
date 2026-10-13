import json
from urllib.parse import parse_qs, urlparse

import pytest
from app.model.documents import decode_file_id, encode_file_id
from conftest import OTHER_BUCKET, PROJECT
from fastapi import HTTPException

BUCKET = PROJECT["s3_bucket"]


@pytest.mark.parametrize(
    "bucket,path",
    [(BUCKET, "reports/summary.docx"), (BUCKET, "ümlaut ?&#/ä.odt"), (OTHER_BUCKET, "a" * 300 + ".xlsx")],
)
def test_file_ids_round_trip_and_are_url_safe(bucket, path):
    file_id = encode_file_id(bucket, path)

    assert decode_file_id(file_id) == (bucket, path)
    assert not set(file_id) & set("/+=?&#")


def test_equal_paths_in_two_buckets_get_different_ids():
    assert encode_file_id(BUCKET, "a.docx") != encode_file_id(OTHER_BUCKET, "a.docx")


@pytest.mark.parametrize("file_id", ["%%%", "bm9zbGFzaA", "L3BhdGg", "YnVja2V0Lw", "_-8"])
def test_invalid_file_ids_are_not_found(file_id):
    with pytest.raises(HTTPException) as error:
        decode_file_id(file_id)
    assert error.value.status_code == 404


def test_lists_only_documents_of_the_project_bucket(client, minio):
    minio.add(BUCKET, "reports/summary.docx")
    minio.add(BUCKET, "notes/protocol.ODT")
    minio.add(BUCKET, "image.png")
    minio.add(BUCKET, "thumbnails/report.docx-thumbnail")
    minio.add(BUCKET, "ignored/.minio.sys/x.docx")
    minio.add(OTHER_BUCKET, "secret.docx")

    response = client.get("/documents/")

    assert response.status_code == 200
    assert minio.listed == [BUCKET]
    assert sorted(doc["file"]["path"] for doc in response.json()) == ["notes/protocol.ODT", "reports/summary.docx"]


def test_document_entry_links_the_preferred_editor(client, minio):
    minio.add(BUCKET, "notes/protocol.odt", b"12345")

    [doc] = client.get("/documents/").json()

    assert doc["file_id"] == encode_file_id(BUCKET, "notes/protocol.odt")
    assert doc["file"] == {
        "bucket": BUCKET,
        "path": "notes/protocol.odt",
        "extension": "odt",
        "modification_time": doc["file"]["modification_time"],
        "size": 5,
    }
    assert doc["app_name"] == "writer"
    assert doc["action_name"] == "edit"
    assert doc["favicon"] == "http://collabora.test/writer.ico"
    url = urlparse(doc["url"])
    assert parse_qs(url.query)["WOPISrc"] == [f"wopi.test:5000/wopi/files/{doc['file_id']}"]


def test_document_url_adds_a_query_separator_when_needed(client, minio):
    minio.add(BUCKET, "analysis/volumes.xlsx")

    [doc] = client.get("/documents/").json()

    assert doc["url"].startswith("http://collabora.test/calc.html?WOPISrc=")


def test_missing_project_header_is_rejected(client):
    response = client.get("/documents/", headers={"Project": ""})

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing Project header"


@pytest.mark.parametrize("header", ["not-json", json.dumps(["project"]), json.dumps({"id": "x"})])
def test_invalid_project_header_is_rejected(client, header):
    response = client.get("/documents/", headers={"Project": header})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Project header"


def test_list_is_unavailable_until_collabora_was_discovered(client, wopi_srv, monkeypatch):
    monkeypatch.setattr(wopi_srv, "apps", [])

    response = client.get("/documents/")

    assert response.status_code == 503
    assert "no document editor" in response.json()["detail"]


def test_denied_bucket_is_forbidden(client, minio):
    minio.denied_buckets.add(BUCKET)

    assert client.get("/documents/").status_code == 403


def test_refresh_endpoint_is_gone(client):
    assert client.post("/documents/refresh").status_code == 405


def test_serves_the_ui(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "<title>Documents</title>" in response.text
