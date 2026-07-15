"""
Unit tests for Workflow API.

Routes covered:
- POST /v1/workflows
- GET /v1/workflows (optional ?title=, ?id=)
- GET /v1/workflows/{workflow_id}
- PATCH /v1/workflows/{workflow_id}
- DELETE /v1/workflows/{workflow_id}
- GET /v1/workflows/{workflow_id}/revisions
- GET /v1/workflows/{workflow_id}/revisions/{increment}
- POST /v1/workflows/{workflow_id}/revisions/{increment}/restore
"""

import sys
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Add current directory to path for test_data
sys.path.insert(0, str(Path(__file__).parent))

from app import models  # noqa: E402
from app.dependencies import require_dev_mode  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from test_data import (  # noqa: E402
    CREATE_WORKFLOW_TEST_CASES,
    VALIDATION_ERROR_TEST_CASES,
    WORKFLOW_BASIC,
)

# ============================================================
# POST /v1/workflows
# ============================================================


@pytest.mark.POST
@pytest.mark.post_workflows
@pytest.mark.parametrize(
    "payload",
    [case[0] for case in CREATE_WORKFLOW_TEST_CASES],
    ids=[case[1] for case in CREATE_WORKFLOW_TEST_CASES],
)
@pytest.mark.asyncio
async def test_create_workflow(client: AsyncClient, payload: dict):
    """First create yields a workflow with increment=1 and the name from the payload."""
    response = await client.post("/v1/workflows", json=payload)
    data = response.json()

    assert response.status_code == 201, data
    assert data["title"] == payload["title"]
    assert data["increment"] == 1
    assert data["id"] is not None
    assert response.headers["Location"] == f"/workflows/{data['id']}"


@pytest.mark.POST
@pytest.mark.post_workflows
@pytest.mark.parametrize(
    "payload,expected_status",
    [(case[0], case[1]) for case in VALIDATION_ERROR_TEST_CASES],
    ids=[case[2] for case in VALIDATION_ERROR_TEST_CASES],
)
@pytest.mark.asyncio
async def test_create_workflow_validation_errors(
    client: AsyncClient, payload: dict, expected_status: int
):
    """Posting wrong workflow payloads yields the expected 422 validation errors."""
    response = await client.post("/v1/workflows", json=payload)
    assert response.status_code == expected_status


@pytest.mark.POST
@pytest.mark.post_workflows
@pytest.mark.asyncio
async def test_create_workflow_existing_title_conflicts(client: AsyncClient):
    """Re-POSTing any payload for an existing title returns 409 with existing_workflow.id in the body."""
    payload = dict(WORKFLOW_BASIC)
    r1 = await client.post("/v1/workflows", json=payload)
    assert r1.status_code == 201
    first_id = r1.json()["id"]

    r2 = await client.post("/v1/workflows", json=payload)
    assert r2.status_code == 409, r2.json()
    detail = r2.json()["detail"]
    assert detail["existing_workflow"]["id"] == first_id


@pytest.mark.POST
@pytest.mark.post_workflows
@pytest.mark.asyncio
async def test_create_workflow_after_soft_delete_creates_new(
    client: AsyncClient,
):
    """POST → DELETE → POST with the same title creates a fresh workflow
    (new id), thanks to the partial unique index on `workflows.title WHERE
    removed=false`."""
    payload = dict(WORKFLOW_BASIC)
    r1 = await client.post("/v1/workflows", json=payload)
    assert r1.status_code == 201
    first_id = r1.json()["id"]

    r_del = await client.delete(f"/v1/workflows/{first_id}")
    assert r_del.status_code == 204

    r2 = await client.post("/v1/workflows", json=payload)
    assert r2.status_code == 201, r2.json()
    assert r2.json()["id"] != first_id


@pytest.mark.POST
@pytest.mark.post_workflows
@pytest.mark.asyncio
async def test_create_workflow_duplicate_labels(client: AsyncClient):
    """Posting a workflow with duplicate (key, value) label pairs returns 422
    via the labels-uniqueness validator on `_MutableWorkflowBase`."""
    payload = {
        "title": "workflow-duplicate-labels",
        "definition": "test_def",
        "workflow_engine": "dummy",
        "labels": [
            {"key": "environment", "value": "production"},
            {"key": "environment", "value": "production"},
        ],
    }
    response = await client.post("/v1/workflows", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()


# ============================================================
# GET /v1/workflows
# ============================================================


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_empty(client: AsyncClient):
    """GET /workflows returns an empty list when no workflows exist."""
    response = await client.get("/v1/workflows")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_returns_latest_revision_fields(
    session: AsyncSession, client: AsyncClient
):
    """When a workflow has multiple revisions, the list response reflects the latest."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "multi-rev",
            "definition": "def-v1",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    _r = await client.patch(f"/v1/workflows/{wf['id']}", json={"definition": "def-v2"})

    assert _r.status_code == 200, _r.text
    _r = await client.patch(f"/v1/workflows/{wf['id']}", json={"definition": "def-v3"})

    assert _r.status_code == 200, _r.text

    response = await client.get("/v1/workflows")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["title"] == "multi-rev"
    assert data[0]["increment"] == 3
    assert data[0]["definition"] == "def-v3"


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_filter_by_name(
    session: AsyncSession, client: AsyncClient
):
    """GET /workflows?title=... filters by title."""
    await client.post(
        "/v1/workflows",
        json={
            "title": "alpha",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )
    await client.post(
        "/v1/workflows",
        json={
            "title": "beta",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    response = await client.get("/v1/workflows?title=alpha")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["title"] == "alpha"


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_pagination(session: AsyncSession, client: AsyncClient):
    """GET /workflows respects skip/limit pagination params."""
    for i in range(5):
        await client.post(
            "/v1/workflows",
            json={
                "title": f"wf-{i}",
                "definition": "test_def",
                "workflow_engine": "dummy",
                "workflow_parameters": [],
                "labels": [],
            },
        )

    r1 = await client.get("/v1/workflows?skip=0&limit=2")
    r2 = await client.get("/v1/workflows?skip=2&limit=2")
    r3 = await client.get("/v1/workflows?skip=4&limit=2")
    assert r1.status_code == r2.status_code == r3.status_code == 200
    assert len(r1.json()) == 2
    assert len(r2.json()) == 2
    assert len(r3.json()) == 1


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_filter_by_id(session: AsyncSession, client: AsyncClient):
    """GET /workflows?id=... filters by workflow UUID."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "wf-id-1",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf1 = _r.json()
    await client.post(
        "/v1/workflows",
        json={
            "title": "wf-id-2",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    response = await client.get(f"/v1/workflows?id={wf1['id']}")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["id"] == str(wf1["id"])


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_order_by_title_asc(
    session: AsyncSession, client: AsyncClient
):
    """GET /workflows?order_by=title&order=asc sorts ascending by title."""
    for t in ["charlie", "alpha", "bravo"]:
        await client.post(
            "/v1/workflows",
            json={
                "title": t,
                "definition": "test_def",
                "workflow_engine": "dummy",
                "workflow_parameters": [],
                "labels": [],
            },
        )

    response = await client.get("/v1/workflows?order_by=title&order=asc")
    data = response.json()
    assert response.status_code == 200
    assert [w["title"] for w in data] == ["alpha", "bravo", "charlie"]


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_order_by_title_desc(
    session: AsyncSession, client: AsyncClient
):
    """GET /workflows?order_by=title&order=desc sorts descending by title."""
    for t in ["charlie", "alpha", "bravo"]:
        await client.post(
            "/v1/workflows",
            json={
                "title": t,
                "definition": "test_def",
                "workflow_engine": "dummy",
                "workflow_parameters": [],
                "labels": [],
            },
        )

    response = await client.get("/v1/workflows?order_by=title&order=desc")
    data = response.json()
    assert response.status_code == 200
    assert [w["title"] for w in data] == ["charlie", "bravo", "alpha"]


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_order_by_id(session: AsyncSession, client: AsyncClient):
    """GET /workflows?order_by=id is accepted (UUID ordering)."""
    for i in range(3):
        await client.post(
            "/v1/workflows",
            json={
                "title": f"id-order-{i}",
                "definition": "test_def",
                "workflow_engine": "dummy",
                "workflow_parameters": [],
                "labels": [],
            },
        )

    response = await client.get("/v1/workflows?order_by=id&order=asc")
    assert response.status_code == 200
    assert len(response.json()) == 3


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_combined_query_params(
    session: AsyncSession, client: AsyncClient
):
    """GET /workflows accepts multiple query params together (order + limit)."""
    for t in ["charlie", "alpha", "bravo", "delta"]:
        await client.post(
            "/v1/workflows",
            json={
                "title": t,
                "definition": "test_def",
                "workflow_engine": "dummy",
                "workflow_parameters": [],
                "labels": [],
            },
        )

    response = await client.get("/v1/workflows?order_by=title&order=asc&limit=2")
    data = response.json()
    assert response.status_code == 200
    assert [w["title"] for w in data] == ["alpha", "bravo"]


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_filter_by_id_with_ordering(
    session: AsyncSession, client: AsyncClient
):
    """Filtering by id combined with ordering still returns the single match."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "id-and-order",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    await client.post(
        "/v1/workflows",
        json={
            "title": "other",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    response = await client.get(f"/v1/workflows?id={wf['id']}&order_by=title&order=asc")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["id"] == str(wf["id"])


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_invalid_order_param(
    session: AsyncSession, client: AsyncClient
):
    """An invalid `order` value falls back to default sort (no error)."""
    for t in ["a", "b"]:
        await client.post(
            "/v1/workflows",
            json={
                "title": t,
                "definition": "test_def",
                "workflow_engine": "dummy",
                "workflow_parameters": [],
                "labels": [],
            },
        )

    response = await client.get("/v1/workflows?order_by=title&order=nonsense")
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_negative_skip(session: AsyncSession, client: AsyncClient):
    """Negative skip is accepted by the API (not validated); behavior is implementation-defined."""
    await client.post(
        "/v1/workflows",
        json={
            "title": "neg-skip",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )
    response = await client.get("/v1/workflows?skip=-1")
    assert response.status_code == 200


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_zero_limit(session: AsyncSession, client: AsyncClient):
    """limit=0 returns an empty list (no error)."""
    await client.post(
        "/v1/workflows",
        json={
            "title": "zero-limit",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )
    response = await client.get("/v1/workflows?limit=0")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_list_workflows_large_limit(session: AsyncSession, client: AsyncClient):
    """A very large limit returns all available rows without erroring."""
    for i in range(3):
        await client.post(
            "/v1/workflows",
            json={
                "title": f"large-limit-{i}",
                "definition": "test_def",
                "workflow_engine": "dummy",
                "workflow_parameters": [],
                "labels": [],
            },
        )
    response = await client.get("/v1/workflows?limit=10000")
    assert response.status_code == 200
    assert len(response.json()) == 3


# ============================================================
# GET /v1/workflows/{workflow_id}
# ============================================================


@pytest.mark.GET
@pytest.mark.get_workflow_by_id
@pytest.mark.asyncio
async def test_get_workflow_by_id(session: AsyncSession, client: AsyncClient):
    """GET /workflows/{id} returns the workflow with its latest revision merged in."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "by-id",
            "definition": "def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    response = await client.get(f"/v1/workflows/{wf['id']}")
    data = response.json()
    assert response.status_code == 200
    assert data["id"] == str(wf["id"])
    assert data["title"] == "by-id"


@pytest.mark.GET
@pytest.mark.get_workflow_by_id
@pytest.mark.asyncio
async def test_get_workflow_by_id_not_found(client: AsyncClient):
    """GET /workflows/{id} returns 404 for an unknown UUID."""
    response = await client.get("/v1/workflows/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.GET
@pytest.mark.get_workflow_by_id
@pytest.mark.asyncio
async def test_get_workflow_by_id_invalid_uuid(client: AsyncClient):
    """GET /workflows/{id} returns 422 when the id isn't a valid UUID."""
    response = await client.get("/v1/workflows/not-a-uuid")
    assert response.status_code == 422


# ============================================================
# PATCH /v1/workflows/{workflow_id}
# ============================================================


@pytest.mark.patch_workflow
@pytest.mark.asyncio
async def test_patch_workflow_definition_bumps_increment(
    session: AsyncSession, client: AsyncClient
):
    """PATCH with a definition change appends a new revision and bumps increment."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "patch-def",
            "definition": "v1",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    response = await client.patch(
        f"/v1/workflows/{wf['id']}", json={"definition": "v2"}
    )
    data = response.json()
    assert response.status_code == 200, data
    assert data["increment"] == 2
    assert data["definition"] == "v2"
    # name unchanged
    assert data["title"] == "patch-def"


@pytest.mark.patch_workflow
@pytest.mark.asyncio
async def test_patch_workflow_title_only_updates_in_place_no_new_revision(
    session: AsyncSession, client: AsyncClient
):
    """Title is not a versioned field — renaming applies in place without
    creating a new revision or bumping the increment."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "old-name",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    response = await client.patch(
        f"/v1/workflows/{wf['id']}", json={"title": "new-title"}
    )
    data = response.json()
    assert response.status_code == 200
    assert data["title"] == "new-title"
    assert data["increment"] == 1


@pytest.mark.patch_workflow
@pytest.mark.asyncio
async def test_patch_workflow_unknown_field_rejected(
    session: AsyncSession, client: AsyncClient
):
    """PATCH with an unknown field is rejected (extra='forbid' on WorkflowUpdate)."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "strict-patch",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    response = await client.patch(f"/v1/workflows/{wf['id']}", json={"id": "12345"})
    assert response.status_code == 422


# ============================================================
# Immutable labels (`kaapana.immutable.*`)
# ============================================================


@pytest.mark.patch_workflow
@pytest.mark.asyncio
async def test_patch_workflow_immutable_label_value_change_rejected(
    session: AsyncSession, client: AsyncClient
):
    """Changing the value of an existing kaapana.immutable.* label is rejected with 422."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "immutable-change",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [
                {"key": "kaapana.immutable.extension.id", "value": "ext-1"},
            ],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    response = await client.patch(
        f"/v1/workflows/{wf['id']}",
        json={
            "labels": [
                {"key": "kaapana.immutable.extension.id", "value": "ext-2"},
            ]
        },
    )
    assert response.status_code == 422
    assert "kaapana.immutable.extension.id" in response.json()["detail"]


@pytest.mark.patch_workflow
@pytest.mark.asyncio
async def test_patch_workflow_immutable_label_removal_rejected(
    session: AsyncSession, client: AsyncClient
):
    """Omitting a previously-present kaapana.immutable.* label is rejected as removal."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "immutable-remove",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [
                {"key": "kaapana.immutable.extension.id", "value": "ext-1"},
                {"key": "kaapana-ui.category", "value": "brain"},
            ],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    response = await client.patch(
        f"/v1/workflows/{wf['id']}",
        json={"labels": [{"key": "kaapana-ui.category", "value": "brain"}]},
    )
    assert response.status_code == 422
    assert "kaapana.immutable.extension.id" in response.json()["detail"]


@pytest.mark.patch_workflow
@pytest.mark.asyncio
async def test_patch_workflow_add_immutable_label_allowed(
    session: AsyncSession, client: AsyncClient
):
    """Adding a new kaapana.immutable.* label (none present before) is allowed."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "immutable-add",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    response = await client.patch(
        f"/v1/workflows/{wf['id']}",
        json={
            "labels": [
                {"key": "kaapana.immutable.extension.id", "value": "ext-1"},
            ]
        },
    )
    assert response.status_code == 200, response.json()
    assert any(
        l["key"] == "kaapana.immutable.extension.id" and l["value"] == "ext-1"
        for l in response.json()["labels"]
    )


@pytest.mark.patch_workflow
@pytest.mark.asyncio
async def test_patch_workflow_add_extra_immutable_label_preserving_existing_allowed(
    session: AsyncSession, client: AsyncClient
):
    """Adding a second immutable label while preserving the first is allowed."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "immutable-add-extra",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [{"key": "kaapana.immutable.extension.id", "value": "ext-1"}],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    response = await client.patch(
        f"/v1/workflows/{wf['id']}",
        json={
            "labels": [
                {"key": "kaapana.immutable.extension.id", "value": "ext-1"},
                {"key": "kaapana.immutable.extension.name", "value": "my-ext"},
            ]
        },
    )
    assert response.status_code == 200, response.json()


@pytest.mark.patch_workflow
@pytest.mark.asyncio
async def test_patch_workflow_mutable_label_changes_allowed(
    session: AsyncSession, client: AsyncClient
):
    """Mutable labels (without the kaapana.immutable. prefix) can be freely changed."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "mutable-change",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [{"key": "kaapana-ui.category", "value": "brain"}],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    response = await client.patch(
        f"/v1/workflows/{wf['id']}",
        json={"labels": [{"key": "kaapana-ui.category", "value": "lung"}]},
    )
    assert response.status_code == 200, response.json()


@pytest.mark.restore_workflow_revision
@pytest.mark.asyncio
async def test_restore_revision_rejected_if_it_would_remove_immutable_label(
    session: AsyncSession, client: AsyncClient
):
    """Restoring to an earlier revision that lacks a now-immutable label is rejected with 422."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "immutable-restore",
            "definition": "v1",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    # Revision 2 adds an immutable label.
    _r = await client.patch(
        f"/v1/workflows/{wf['id']}",
        json={
            "definition": "v2",
            "labels": [
                {"key": "kaapana.immutable.extension.id", "value": "ext-1"},
            ],
        },
    )

    assert _r.status_code == 200, _r.text
    # Restoring to revision 1 would remove the immutable label → 422.
    response = await client.post(f"/v1/workflows/{wf['id']}/revisions/1/restore")
    assert response.status_code == 422
    assert "kaapana.immutable.extension.id" in response.json()["detail"]


# ============================================================
# DELETE /v1/workflows/{workflow_id}
# ============================================================


@pytest.mark.DELETE
@pytest.mark.delete_workflow
@pytest.mark.asyncio
async def test_delete_workflow(session: AsyncSession, client: AsyncClient):
    """DELETE soft-deletes the workflow; subsequent GETs return 404."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "to-delete",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    response = await client.delete(f"/v1/workflows/{wf['id']}")
    assert response.status_code == 204

    # Not findable
    response = await client.get(f"/v1/workflows/{wf['id']}")
    assert response.status_code == 404

    # But persisted in DB with removed=True
    from sqlalchemy import select

    import uuid as _uuid

    stmt = select(models.Workflow).where(models.Workflow.id == _uuid.UUID(wf["id"]))
    result = await session.execute(stmt)
    db_wf = result.scalars().first()
    assert db_wf is not None
    assert db_wf.removed is True


@pytest.mark.DELETE
@pytest.mark.delete_workflow
@pytest.mark.asyncio
async def test_delete_workflow_twice_returns_404(
    session: AsyncSession, client: AsyncClient
):
    """Deleting an already soft-deleted workflow returns 404."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "double-delete",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    r1 = await client.delete(f"/v1/workflows/{wf['id']}")
    assert r1.status_code == 204
    r2 = await client.delete(f"/v1/workflows/{wf['id']}")
    assert r2.status_code == 404


# ============================================================
# Revisions
# ============================================================


@pytest.mark.get_workflow_revisions
@pytest.mark.asyncio
async def test_list_revisions(session: AsyncSession, client: AsyncClient):
    """GET /workflows/{id}/revisions returns all revisions in increment order."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "rev-list",
            "definition": "v1",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    _r = await client.patch(f"/v1/workflows/{wf['id']}", json={"definition": "v2"})

    assert _r.status_code == 200, _r.text
    _r = await client.patch(f"/v1/workflows/{wf['id']}", json={"definition": "v3"})

    assert _r.status_code == 200, _r.text

    response = await client.get(f"/v1/workflows/{wf['id']}/revisions")
    data = response.json()
    assert response.status_code == 200
    assert [r["increment"] for r in data] == [1, 2, 3]
    assert [r["definition"] for r in data] == ["v1", "v2", "v3"]


@pytest.mark.get_workflow_revisions
@pytest.mark.asyncio
async def test_get_specific_revision(session: AsyncSession, client: AsyncClient):
    """GET /workflows/{id}/revisions/{n} returns the specific revision snapshot."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "rev-get",
            "definition": "v1",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    _r = await client.patch(f"/v1/workflows/{wf['id']}", json={"definition": "v2"})

    assert _r.status_code == 200, _r.text

    response = await client.get(f"/v1/workflows/{wf['id']}/revisions/1")
    data = response.json()
    assert response.status_code == 200
    assert data["increment"] == 1
    assert data["definition"] == "v1"


@pytest.mark.get_workflow_revisions
@pytest.mark.asyncio
async def test_get_revision_not_found(session: AsyncSession, client: AsyncClient):
    """GET /workflows/{id}/revisions/{n} returns 404 for an unknown increment."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "rev-missing",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    response = await client.get(f"/v1/workflows/{wf['id']}/revisions/99")
    assert response.status_code == 404


@pytest.mark.restore_workflow_revision
@pytest.mark.asyncio
async def test_restore_revision_creates_new_increment_with_old_content(
    session: AsyncSession, client: AsyncClient
):
    """Restoring revision 1 from a workflow at increment 3 produces increment 4 with v1's content."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "rev-restore",
            "definition": "v1",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    _r = await client.patch(f"/v1/workflows/{wf['id']}", json={"definition": "v2"})

    assert _r.status_code == 200, _r.text
    _r = await client.patch(f"/v1/workflows/{wf['id']}", json={"definition": "v3"})

    assert _r.status_code == 200, _r.text

    response = await client.post(f"/v1/workflows/{wf['id']}/revisions/1/restore")
    data = response.json()
    assert response.status_code == 200
    assert data["increment"] == 4
    assert data["definition"] == "v1"


# ============================================================
# DEV_MODE gating updates
# ============================================================


@pytest.mark.patch_workflow
@pytest.mark.asyncio
async def test_patch_workflow_forbidden_when_dev_mode_off(
    session: AsyncSession, client: AsyncClient
):
    """PATCH /workflows/{id} returns 403 when DEV_MODE is off."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "dev-gated-patch",
            "definition": "v1",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    fastapi_app.dependency_overrides[require_dev_mode] = require_dev_mode
    try:
        response = await client.patch(
            f"/v1/workflows/{wf['id']}", json={"definition": "v2"}
        )
    finally:
        fastapi_app.dependency_overrides[require_dev_mode] = lambda: None
    assert response.status_code == 403
    assert "DEV_MODE" in response.json()["detail"]


@pytest.mark.restore_workflow_revision
@pytest.mark.asyncio
async def test_restore_revision_forbidden_when_dev_mode_off(
    session: AsyncSession, client: AsyncClient
):
    """POST /workflows/{id}/revisions/{n}/restore returns 403 when DEV_MODE is off."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "dev-gated-restore",
            "definition": "v1",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    _r = await client.patch(f"/v1/workflows/{wf['id']}", json={"definition": "v2"})

    assert _r.status_code == 200, _r.text
    fastapi_app.dependency_overrides[require_dev_mode] = require_dev_mode
    try:
        response = await client.post(f"/v1/workflows/{wf['id']}/revisions/1/restore")
    finally:
        fastapi_app.dependency_overrides[require_dev_mode] = lambda: None
    assert response.status_code == 403
    assert "DEV_MODE" in response.json()["detail"]


# =======================================================
# Airflow DAGs overwritten during POST -> DELETE -> POST
# =======================================================


def test_dag_id_collides_after_soft_delete_with_same_title():
    """Regression pin for a known sharp edge: soft-delete doesn't propagate to engine adapters and the Airflow dag_id omits the workflow UUID, so POST -> DELETE -> POST with the same title produces a colliding dag_id and overwrites the prior DAG file on disk."""
    from app.adapters.adapters.airflow_adapter import AirflowPluginAdapter

    dag_id_old = AirflowPluginAdapter._get_dag_id_from_workflow(
        AirflowPluginAdapter, "my-workflow", 1
    )
    dag_id_new = AirflowPluginAdapter._get_dag_id_from_workflow(
        AirflowPluginAdapter, "my-workflow", 1
    )
    assert dag_id_old == dag_id_new == "my-workflow_inc1"
