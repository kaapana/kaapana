"""Unit tests for DataClient — async, no network (httpx.MockTransport)."""

import json

import httpx

from data_api import DataClient


def _client(handler):
    return DataClient(
        base_url="http://data-api/v1", transport=httpx.MockTransport(handler)
    )


async def test_query_index_collects_items():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200, json={"total_count": 2, "items": ["a", "b"], "next_cursor": None}
        )

    async with _client(handler) as client:
        ids = await client.query_index(
            {"type": "filter", "field": "metadata.model", "op": "has_key"}
        )

    assert ids == ["a", "b"]
    assert calls[0].url.path.endswith("/entities/query/index")
    body = json.loads(calls[0].content)
    assert body["where"]["op"] == "has_key"


async def test_query_index_paginates_on_cursor():
    pages = [
        {"items": ["a"], "next_cursor": "c1"},
        {"items": ["b"], "next_cursor": None},
    ]
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=pages[len(bodies) - 1])

    async with _client(handler) as client:
        assert await client.query_index(None) == ["a", "b"]

    assert len(bodies) == 2
    assert bodies[1]["cursor"] == "c1"


async def test_resolve_dataset_members_builds_descendant_query():
    captured = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"items": ["m1"], "next_cursor": None})

    extra = {"type": "filter", "field": "metadata.model", "op": "has_key"}
    async with _client(handler) as client:
        ids = await client.resolve_dataset_members("ds-1", extra_where=extra)

    assert ids == ["m1"]
    where = captured["body"]["where"]
    assert where["op"] == "and"
    by_op = {c["op"]: c for c in where["children"]}
    assert "has_key" in by_op
    assert by_op["descendant_of"]["value"] == {
        "entity_id": "ds-1",
        "link_type": "contains",
    }


def test_get_storage_coordinates_reads_field():
    assert DataClient.get_storage_coordinates(
        {"storage_coordinates": [{"type": "s3"}]}
    ) == [{"type": "s3"}]
    assert DataClient.get_storage_coordinates({}) == []


async def test_register_metadata_schema_posts_to_key():
    captured = {}

    def handler(request):
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"key": "model", "schema": captured["body"]})

    schema = {"type": "object", "additionalProperties": True}
    async with _client(handler) as client:
        out = await client.register_metadata_schema("model", schema)

    assert captured["path"].endswith("/metadata/keys/model")
    assert captured["body"] == schema
    assert out["key"] == "model"


async def test_create_entity_and_attach_metadata():
    seen = []

    def handler(request):
        seen.append((request.method, request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"id": "e1"})

    async with _client(handler) as client:
        await client.create_entity(
            {"id": "e1", "storage_coordinates": [], "metadata": []}
        )
        await client.attach_metadata(
            "e1", "permissions", {"project": "p", "owner": None}
        )

    assert seen[0][0] == "POST" and seen[0][1].endswith("/entities")
    assert seen[1][1].endswith("/entities/e1/metadata")
    assert seen[1][2] == {
        "key": "permissions",
        "data": {"project": "p", "owner": None},
        "artifacts": [],
    }


async def test_auth_token_forwarded_as_headers():
    captured = {}

    def handler(request):
        captured["auth"] = request.headers.get("authorization")
        captured["fwd"] = request.headers.get("x-forwarded-access-token")
        return httpx.Response(200, json={"items": [], "next_cursor": None})

    client = DataClient(
        base_url="http://data-api/v1",
        access_token="tok",
        transport=httpx.MockTransport(handler),
    )
    async with client:
        await client.query_index(None)

    assert captured["auth"] == "Bearer tok"
    assert captured["fwd"] == "tok"
