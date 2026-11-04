import datetime

import pytest
from app.model.documents import encode_file_id
from app.model.wopi import WOPI, editor_url, parse_discovery
from app.routers import wopi as wopi_router
from conftest import OTHER_BUCKET, PROJECT

BUCKET = PROJECT["s3_bucket"]
DOCUMENT = "reports/summary.docx"
FILE_ID = encode_file_id(BUCKET, DOCUMENT)

DISCOVERY = b"""<?xml version="1.0" encoding="utf-8"?>
<wopi-discovery>
  <net-zone name="external-http">
    <app name="application/vnd.oasis.opendocument.text">
      <action default="true" ext="" name="edit" urlsrc="http://collabora.test/cool.html?"/>
    </app>
    <app favIconUrl="http://collabora.test/writer.ico" name="writer">
      <action ext="ODT" name="view" urlsrc="http://collabora.test/cool.html?"/>
      <action ext="odt" name="edit" urlsrc="http://collabora.test/cool.html?"/>
    </app>
    <app name="Capabilities">
      <action ext="" name="getinfo" urlsrc="http://collabora.test/capabilities"/>
    </app>
  </net-zone>
</wopi-discovery>"""


def test_discovery_keeps_only_extension_based_actions():
    [app] = parse_discovery(DISCOVERY)

    assert app.name == "writer"
    assert app.favicon == "http://collabora.test/writer.ico"
    assert [(a.extension, a.name) for a in app.actions] == [("odt", "view"), ("odt", "edit")]


def test_match_prefers_edit_and_ignores_case():
    wopi_srv = WOPI("http://collabora.test/hosting/discovery")
    wopi_srv.apps = parse_discovery(DISCOVERY)

    assert wopi_srv.match("ODT").action.name == "edit"
    assert wopi_srv.match("pdf") is None
    assert wopi_srv.supported_extensions() == {"odt"}


@pytest.mark.parametrize(
    "urlsrc,expected",
    [
        ("http://c/cool.html?", "http://c/cool.html?WOPISrc=w"),
        ("http://c/cool.html?lang=de&", "http://c/cool.html?lang=de&WOPISrc=w"),
        ("http://c/cool.html?lang=de", "http://c/cool.html?lang=de&WOPISrc=w"),
        ("http://c/cool.html", "http://c/cool.html?WOPISrc=w"),
    ],
)
def test_editor_url(urlsrc, expected):
    assert editor_url(urlsrc, "w") == expected


def test_check_file_info(client, minio, monkeypatch):
    monkeypatch.setattr(wopi_router, "can_write", lambda token, bucket: True)
    minio.add(BUCKET, DOCUMENT, b"12345")

    response = client.get(f"/wopi/files/{FILE_ID}", headers={"x-forwarded-preferred-username": "kaapana"})

    assert response.status_code == 200
    info = response.json()
    assert info["BaseFileName"] == "summary.docx"
    assert info["Size"] == 5
    assert info["OwnerId"] == BUCKET
    assert info["UserId"] == "kaapana"
    assert info["UserFriendlyName"] == "kaapana"
    assert info["UserCanWrite"] is True
    assert info["ReadOnly"] is False
    assert info["Version"]
    assert datetime.datetime.fromisoformat(info["LastModifiedTime"]).tzinfo is not None


def test_check_file_info_is_read_only_without_write_access(client, minio, monkeypatch):
    monkeypatch.setattr(wopi_router, "can_write", lambda token, bucket: False)
    minio.add(BUCKET, DOCUMENT)

    info = client.get(f"/wopi/files/{FILE_ID}").json()

    assert info["UserCanWrite"] is False
    assert info["ReadOnly"] is True
    assert info["SupportsUpdate"] is False


def test_check_file_info_of_a_missing_file_is_not_found(client):
    assert client.get(f"/wopi/files/{FILE_ID}").status_code == 404


def test_check_file_info_of_a_denied_bucket_is_forbidden(client, minio):
    minio.add(OTHER_BUCKET, DOCUMENT)
    minio.denied_buckets.add(OTHER_BUCKET)

    assert client.get(f"/wopi/files/{encode_file_id(OTHER_BUCKET, DOCUMENT)}").status_code == 403


def test_get_file_streams_binary_content_and_releases_the_connection(client, minio):
    content = bytes(range(256)) * 1000
    minio.add(BUCKET, DOCUMENT, content)

    response = client.get(f"/wopi/files/{FILE_ID}/contents")

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["X-WOPI-ItemVersion"]
    assert minio.responses[-1].closed and minio.responses[-1].released


def test_put_file_stores_the_raw_body(client, minio):
    minio.add(BUCKET, DOCUMENT, b"old")
    content = b"\x50\x4b\x03\x04 new"

    response = client.post(
        f"/wopi/files/{FILE_ID}/contents",
        content=content,
        headers={"X-WOPI-Override": "PUT", "Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 200
    assert minio.objects[(BUCKET, DOCUMENT)][0] == content
    assert response.json()["LastModifiedTime"]
    assert response.headers["X-WOPI-ItemVersion"]


def test_put_file_with_the_current_timestamp_succeeds(client, minio):
    minio.add(BUCKET, DOCUMENT, b"old")
    timestamp = client.get(f"/wopi/files/{FILE_ID}").json()["LastModifiedTime"]

    response = client.post(
        f"/wopi/files/{FILE_ID}/contents", content=b"new", headers={"X-COOL-WOPI-Timestamp": timestamp}
    )

    assert response.status_code == 200
    assert minio.objects[(BUCKET, DOCUMENT)][0] == b"new"


def test_put_file_does_not_overwrite_a_document_changed_meanwhile(client, minio):
    minio.add(BUCKET, DOCUMENT, b"old")
    timestamp = client.get(f"/wopi/files/{FILE_ID}").json()["LastModifiedTime"]
    minio.add(BUCKET, DOCUMENT, b"changed elsewhere")

    response = client.post(
        f"/wopi/files/{FILE_ID}/contents", content=b"new", headers={"X-COOL-WOPI-Timestamp": timestamp}
    )

    assert response.status_code == 409
    assert response.json() == {"COOLStatusCode": 1010}
    assert minio.objects[(BUCKET, DOCUMENT)][0] == b"changed elsewhere"


def test_put_file_into_a_denied_bucket_is_forbidden(client, minio):
    minio.add(BUCKET, DOCUMENT, b"old")
    minio.denied_buckets.add(BUCKET)

    assert client.post(f"/wopi/files/{FILE_ID}/contents", content=b"new").status_code == 403


def test_saving_announces_an_update_to_sockets_of_the_same_project(client, minio):
    minio.add(BUCKET, DOCUMENT, b"old")

    with client.websocket_connect("/ws") as socket:
        client.post(f"/wopi/files/{FILE_ID}/contents", content=b"new")
        assert socket.receive_json() == {"type": "update"}


def test_saving_does_not_announce_to_other_projects(client, minio):
    from app.dependencies import get_connection_manager

    minio.add(OTHER_BUCKET, DOCUMENT, b"old")

    with client.websocket_connect("/ws"):
        client.post(f"/wopi/files/{encode_file_id(OTHER_BUCKET, DOCUMENT)}/contents", content=b"new")
        assert set(get_connection_manager().active_connections) == {BUCKET}


def test_socket_without_project_is_closed(client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/ws", headers={"Project": ""}) as socket:
            socket.receive_json()
    assert error.value.code == 1008


def test_discovery_keeps_retrying_until_collabora_answers(monkeypatch):
    import asyncio

    from app import main
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "discovery_retry_seconds", 0)
    monkeypatch.setattr(get_settings(), "discovery_interval_seconds", 0)
    wopi_srv = WOPI("http://collabora.test/hosting/discovery")
    attempts = []

    def fetch_apps():
        attempts.append(1)
        if len(attempts) < 3:
            raise ConnectionError("collabora is still starting")
        wopi_srv.apps = parse_discovery(DISCOVERY)

    monkeypatch.setattr(wopi_srv, "fetch_apps", fetch_apps)

    async def run():
        task = asyncio.create_task(main.wopi_discovery_task(wopi_srv))
        while not wopi_srv.apps:
            await asyncio.sleep(0.01)
        task.cancel()

    asyncio.run(asyncio.wait_for(run(), 5))
    assert len(attempts) >= 3
