import pytest
from conftest import entity_payload

pytestmark = pytest.mark.anyio

SAMPLE_SCHEMA = {"type": "object", "properties": {"modality": {"type": "string"}}}


async def create_entity_with_artifacts(client) -> str:
    assert (await client.post("/v1/metadata/keys/sample", json=SAMPLE_SCHEMA)).status_code == 200
    payload = entity_payload(sample={"modality": "CT"})
    assert (await client.post("/v1/entities", json=payload)).status_code == 200
    for artifact_id in ("thumbnail", "report"):
        uploaded = await client.post(
            f"/v1/entities/{payload['id']}/metadata/sample/artifacts/{artifact_id}",
            files={"file": (f"{artifact_id}.bin", artifact_id.encode(), "application/octet-stream")},
        )
        assert uploaded.status_code == 200
    return payload["id"]


async def test_saving_a_metadata_entry_keeps_the_files_of_its_artifacts(client) -> None:
    entity_id = await create_entity_with_artifacts(client)
    entity = (await client.get(f"/v1/entities/{entity_id}")).json()
    artifacts = entity["metadata"][0]["artifacts"]

    saved = await client.post(
        f"/v1/entities/{entity_id}/metadata",
        json={"key": "sample", "data": {"modality": "MR"}, "artifacts": artifacts},
    )
    assert saved.status_code == 200

    for artifact_id in ("thumbnail", "report"):
        download = await client.get(f"/v1/entities/{entity_id}/metadata/sample/artifacts/{artifact_id}")
        assert download.status_code == 200
        assert download.content == artifact_id.encode()


async def test_artifacts_left_out_of_a_saved_entry_are_deleted(client) -> None:
    entity_id = await create_entity_with_artifacts(client)
    entity = (await client.get(f"/v1/entities/{entity_id}")).json()
    kept = [artifact for artifact in entity["metadata"][0]["artifacts"] if artifact["id"] == "thumbnail"]

    saved = await client.post(
        f"/v1/entities/{entity_id}/metadata",
        json={"key": "sample", "data": {"modality": "MR"}, "artifacts": kept},
    )
    assert [artifact["id"] for artifact in saved.json()["metadata"][0]["artifacts"]] == ["thumbnail"]

    assert (await client.get(f"/v1/entities/{entity_id}/metadata/sample/artifacts/thumbnail")).status_code == 200
    from app.services.artifact_store import get_artifact_store

    assert not get_artifact_store()._path_for(entity_id, "sample", "report").exists()
