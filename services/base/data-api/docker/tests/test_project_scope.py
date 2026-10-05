import asyncio
import json

import pytest
from app.services.event_bus import EventBus
from app.services.project_scope import PERMISSIONS_SCHEMA, InvalidProjectHeader, parse_project_header
from conftest import PROJECT_A, PROJECT_B, entity_payload, project_header

pytestmark = pytest.mark.anyio

SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {"modality": {"type": "string"}},
}


async def register_schemas(client) -> None:
    for key, schema in (("sample", SAMPLE_SCHEMA), ("permissions", PERMISSIONS_SCHEMA)):
        response = await client.post(f"/v1/metadata/keys/{key}", json=schema)
        assert response.status_code == 200


async def seed(client) -> dict[str, str]:
    await register_schemas(client)
    ids = {}
    for name, project, modality in (
        ("a", PROJECT_A, "CT"),
        ("b", PROJECT_B, "MR"),
        ("orphan", None, "PT"),
    ):
        payload = entity_payload(project, sample={"modality": modality})
        response = await client.post("/v1/entities", json=payload)
        assert response.status_code == 200
        ids[name] = payload["id"]
    return ids


def test_parse_project_header() -> None:
    assert parse_project_header(None) is None
    assert parse_project_header("") is None
    assert parse_project_header(json.dumps({"id": PROJECT_A})).id == PROJECT_A
    for invalid in ("not json", "[]", json.dumps({"name": "x"}), json.dumps({"id": ""})):
        with pytest.raises(InvalidProjectHeader):
            parse_project_header(invalid)


async def test_invalid_project_header_is_rejected(client) -> None:
    response = await client.get("/v1/entities", headers={"Project": "not json"})
    assert response.status_code == 400


async def test_listings_only_contain_entities_of_the_project(client) -> None:
    ids = await seed(client)
    scoped = project_header(PROJECT_A)

    listed = await client.get("/v1/entities", headers=scoped)
    assert listed.json()["items"] == [ids["a"]]

    index = await client.get("/v1/entities/index/full", headers=scoped)
    assert index.json() == {"total_count": 1, "items": [ids["a"]], "next_cursor": None}

    records = await client.get("/v1/entities/records", headers=scoped)
    assert [record["id"] for record in records.json()["items"]] == [ids["a"]]

    unscoped = await client.get("/v1/entities/index/full")
    assert unscoped.json()["total_count"] == 3


async def test_queries_are_restricted_to_the_project(client) -> None:
    ids = await seed(client)
    match_all_modalities = {
        "where": {"type": "filter", "field": "metadata.sample.modality", "op": "in", "value": ["CT", "MR", "PT"]}
    }

    query = await client.post("/v1/entities/query", json=match_all_modalities, headers=project_header(PROJECT_B))
    body = query.json()
    assert body["total_count"] == 1
    assert [entity["id"] for entity in body["results"]] == [ids["b"]]

    index = await client.post("/v1/entities/query/index", json=match_all_modalities, headers=project_header(PROJECT_B))
    assert index.json()["items"] == [ids["b"]]

    unfiltered = await client.post("/v1/entities/query", json={}, headers=project_header(PROJECT_A))
    assert unfiltered.json()["total_count"] == 1


async def test_entities_of_other_projects_are_not_found(client) -> None:
    ids = await seed(client)
    scoped = project_header(PROJECT_A)
    foreign = ids["b"]

    assert (await client.get(f"/v1/entities/{foreign}", headers=scoped)).status_code == 404
    assert (await client.get(f"/v1/entities/{ids['orphan']}", headers=scoped)).status_code == 404
    assert (await client.delete(f"/v1/entities/{foreign}", headers=scoped)).status_code == 404
    assert (
        await client.post(
            f"/v1/entities/{foreign}/metadata",
            json={"key": "sample", "data": {"modality": "XA"}},
            headers=scoped,
        )
    ).status_code == 404
    assert (await client.delete(f"/v1/entities/{foreign}/metadata/sample", headers=scoped)).status_code == 404
    assert (
        await client.post(
            f"/v1/entities/{foreign}/storage-coordinates",
            json={"type": "filesystem", "volume": "data", "path": "/x"},
            headers=scoped,
        )
    ).status_code == 404
    assert (
        await client.post(
            f"/v1/entities/{foreign}/metadata/sample/artifacts/thumb",
            files={"file": ("thumb.png", b"png", "image/png")},
            headers=scoped,
        )
    ).status_code == 404
    assert (
        await client.get(f"/v1/entities/{foreign}/metadata/sample/artifacts/thumb", headers=scoped)
    ).status_code == 404

    untouched = await client.get(f"/v1/entities/{foreign}")
    assert untouched.status_code == 200
    assert untouched.json()["metadata"][0]["data"] == {"modality": "MR"}


async def test_entities_of_the_project_can_be_edited(client) -> None:
    ids = await seed(client)
    scoped = project_header(PROJECT_A)
    own = ids["a"]

    updated = await client.post(
        f"/v1/entities/{own}/metadata", json={"key": "sample", "data": {"modality": "XA"}}, headers=scoped
    )
    assert updated.status_code == 200

    uploaded = await client.post(
        f"/v1/entities/{own}/metadata/sample/artifacts/thumb",
        files={"file": ("thumb.png", b"png", "image/png")},
        headers=scoped,
    )
    assert uploaded.status_code == 200
    download = await client.get(f"/v1/entities/{own}/metadata/sample/artifacts/thumb", headers=scoped)
    assert download.content == b"png"

    assert (await client.delete(f"/v1/entities/{own}", headers=scoped)).status_code == 204
    assert (await client.get(f"/v1/entities/{own}")).status_code == 404


async def test_scoped_create_assigns_the_project(client) -> None:
    payload = entity_payload()
    response = await client.post("/v1/entities", json=payload, headers=project_header(PROJECT_A))
    assert response.status_code == 200
    permissions = [entry for entry in response.json()["metadata"] if entry["key"] == "permissions"]
    assert permissions[0]["data"] == {"project": PROJECT_A, "owner": None}

    schema = await client.get("/v1/metadata/keys/permissions")
    assert schema.status_code == 200

    listed = await client.get("/v1/entities", headers=project_header(PROJECT_A))
    assert listed.json()["items"] == [payload["id"]]


async def test_scoped_create_cannot_target_another_project(client) -> None:
    response = await client.post("/v1/entities", json=entity_payload(PROJECT_B), headers=project_header(PROJECT_A))
    assert response.status_code == 403


async def test_scoped_create_cannot_replace_an_entity_of_another_project(client) -> None:
    ids = await seed(client)
    payload = entity_payload(PROJECT_A)
    payload["id"] = ids["b"]
    response = await client.post("/v1/entities", json=payload, headers=project_header(PROJECT_A))
    assert response.status_code == 409
    assert (await client.get(f"/v1/entities/{ids['b']}", headers=project_header(PROJECT_B))).status_code == 200


async def test_the_permissions_entry_cannot_leave_the_project(client) -> None:
    ids = await seed(client)
    scoped = project_header(PROJECT_A)
    own = ids["a"]

    moved = await client.post(
        f"/v1/entities/{own}/metadata",
        json={"key": "permissions", "data": {"project": PROJECT_B, "owner": None}},
        headers=scoped,
    )
    assert moved.status_code == 403
    removed = await client.delete(f"/v1/entities/{own}/metadata/permissions", headers=scoped)
    assert removed.status_code == 403

    owner_set = await client.post(
        f"/v1/entities/{own}/metadata",
        json={"key": "permissions", "data": {"project": PROJECT_A, "owner": "alice"}},
        headers=scoped,
    )
    assert owner_set.status_code == 200

    unscoped_move = await client.post(
        f"/v1/entities/{own}/metadata",
        json={"key": "permissions", "data": {"project": PROJECT_B, "owner": None}},
    )
    assert unscoped_move.status_code == 200
    assert (await client.get(f"/v1/entities/{own}", headers=project_header(PROJECT_B))).status_code == 200


async def test_field_hints_only_sample_the_project(client) -> None:
    await seed(client)
    scoped = project_header(PROJECT_A)

    fields = await client.get("/v1/metadata/keys/sample/fields", headers=scoped)
    assert fields.json()["total_entries"] == 1
    assert fields.json()["fields"][0]["example"] == "CT"

    values = await client.get("/v1/metadata/keys/sample/field-values", params={"path": "modality"}, headers=scoped)
    assert values.json()["values"] == ["CT"]

    unscoped = await client.get("/v1/metadata/keys/sample/field-values", params={"path": "modality"})
    assert sorted(unscoped.json()["values"]) == ["CT", "MR", "PT"]


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def accept(self) -> None:
        return None

    async def send_text(self, message: str) -> None:
        self.sent.append(json.loads(message))

    async def close(self) -> None:
        return None


async def test_event_bus_only_delivers_entity_events_of_the_project() -> None:
    bus = EventBus()
    socket_a, socket_b, socket_all = FakeWebSocket(), FakeWebSocket(), FakeWebSocket()
    await bus.connect(socket_a, PROJECT_A)
    await bus.connect(socket_b, PROJECT_B)
    await bus.connect(socket_all, None)

    entity_event = {"resource": "data_entity", "action": "updated", "data": {"id": "1"}}
    key_event = {"resource": "metadata_key", "action": "created", "data": {"key": "sample"}}
    await bus.broadcast(entity_event, frozenset({PROJECT_A}))
    await bus.broadcast(key_event)
    await asyncio.sleep(0.05)

    assert socket_a.sent == [{"batch": [entity_event, key_event]}]
    assert socket_b.sent == [key_event]
    assert socket_all.sent == [{"batch": [entity_event, key_event]}]

    for socket in (socket_a, socket_b, socket_all):
        await bus.disconnect(socket)
