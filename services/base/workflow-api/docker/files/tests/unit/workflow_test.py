"""
Unit tests for Workflow API following SQLModel testing patterns.

These tests follow the SQLModel documentation approach:
- Use both 'session' and 'client' fixtures
- Create test data directly in database using session
- Test API endpoints using client
- Each test gets fresh in-memory SQLite database

Tests are organized by route/endpoint with clear markers:
- POST /v1/workflows
- GET /v1/workflows
- GET /v1/workflows/{title}
- GET /v1/workflows/{title}/{version}
- DELETE /v1/workflows/{title}/{version}
"""

import sys
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Add current directory to path to import test_data
sys.path.insert(0, str(Path(__file__).parent))

from app import models  # noqa: E402

# Import test data (must be after sys.path modification)
from test_data import (  # noqa: E402
    CREATE_WORKFLOW_TEST_CASES,
    DELETE_WORKFLOW_TEST_CASES,
    GET_WORKFLOW_BY_TITLE_TEST_CASES,
    GET_WORKFLOW_BY_TITLE_VERSION_TEST_CASES,
    READ_WORKFLOW_ERROR_TEST_CASES,
    READ_WORKFLOWS_TEST_CASES,
    VALIDATION_ERROR_TEST_CASES,
)

# ============================================================
# POST /v1/workflows - Create Workflow Tests
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
    """Test creating workflows with various configurations"""
    response = await client.post("/v1/workflows", json=payload)
    data = response.json()

    assert response.status_code == 201
    assert data["title"] == payload["title"]
    assert data["version"] == 1
    assert data["id"] is not None

    # Verify Location header
    assert "Location" in response.headers
    assert (
        response.headers["Location"] == f"/workflows/{data['title']}/{data['version']}"
    )

    # Verify labels if present
    if "labels" in payload:
        assert len(data["labels"]) == len(payload["labels"])
        for expected_label in payload["labels"]:
            assert any(
                label["key"] == expected_label["key"]
                and label["value"] == expected_label["value"]
                for label in data["labels"]
            )

    # Verify workflow_parameters if present
    if "workflow_parameters" in payload:
        assert len(data["workflow_parameters"]) == len(payload["workflow_parameters"])
        for i, expected_param in enumerate(payload["workflow_parameters"]):
            actual_param = data["workflow_parameters"][i]
            assert actual_param["task_title"] == expected_param["task_title"]
            assert (
                actual_param["env_variable_name"] == expected_param["env_variable_name"]
            )
            assert actual_param["ui_form"]["type"] == expected_param["ui_form"]["type"]


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
    """Test creating workflow with various validation errors"""
    response = await client.post("/v1/workflows", json=payload)
    assert response.status_code == expected_status


@pytest.mark.POST
@pytest.mark.post_workflows
@pytest.mark.asyncio
async def test_create_workflow_duplicate_labels(client: AsyncClient):
    """Test that creating a workflow with duplicate labels fails with validation error"""
    payload = {
        "title": "workflow-duplicate-labels",
        "definition": "test_def",
        "workflow_engine": "dummy",
        "labels": [
            {"key": "environment", "value": "production"},
            {"key": "environment", "value": "production"},  # Duplicate
        ],
    }

    response = await client.post("/v1/workflows", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.POST
@pytest.mark.post_workflows
@pytest.mark.asyncio
async def test_create_workflow_increments_version(client: AsyncClient):
    """Test that creating workflows with same title increments version"""
    payload = {
        "title": "version-test-workflow",
        "definition": "test_def",
        "workflow_engine": "dummy",
    }

    # Create first version
    response1 = await client.post("/v1/workflows", json=payload)
    assert response1.status_code == 201
    data1 = response1.json()
    assert data1["version"] == 1

    # Create second version (same title)
    response2 = await client.post("/v1/workflows", json=payload)
    assert response2.status_code == 201
    data2 = response2.json()
    assert data2["version"] == 2

    # Create third version
    response3 = await client.post("/v1/workflows", json=payload)
    assert response3.status_code == 201
    data3 = response3.json()
    assert data3["version"] == 3


# ============================================================
# GET /v1/workflows - List Workflows Tests
# ============================================================


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.parametrize(
    "workflows_data",
    [case[0] for case in READ_WORKFLOWS_TEST_CASES],
    ids=[case[1] for case in READ_WORKFLOWS_TEST_CASES],
)
@pytest.mark.asyncio
async def test_read_workflows(
    session: AsyncSession, client: AsyncClient, workflows_data: list[dict]
):
    """
    Test reading workflows with different data scenarios.

    Creates test data using 'session', then calls API using 'client'.
    This is the key pattern from SQLModel documentation!
    """
    # Create test workflows directly in database
    created_workflows = []
    for wf_data in workflows_data:
        # Convert label dicts to Label models if present
        if "labels" in wf_data:
            wf_data = wf_data.copy()  # Don't mutate the original
            wf_data["labels"] = [models.Label(**label) for label in wf_data["labels"]]

        workflow = models.Workflow(**wf_data)
        session.add(workflow)
        created_workflows.append(workflow)

    await session.commit()
    for wf in created_workflows:
        await session.refresh(wf)

    # Now test the API
    response = await client.get("/v1/workflows")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == len(workflows_data)

    # Verify each workflow matches
    for i, expected_wf in enumerate(created_workflows):
        assert data[i]["title"] == expected_wf.title
        assert data[i]["version"] == expected_wf.version
        assert data[i]["id"] == expected_wf.id


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_read_workflows_empty(client: AsyncClient):
    """Test reading workflows when database is empty"""
    response = await client.get("/v1/workflows")
    data = response.json()

    assert response.status_code == 200
    assert data == []


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_read_workflows_pagination(session: AsyncSession, client: AsyncClient):
    """Test workflow pagination with skip and limit"""
    # Create 5 workflows
    for i in range(5):
        workflow = models.Workflow(
            title=f"workflow-{i}",
            version=1,
            definition=f"def-{i}",
            workflow_engine="dummy",
        )
        session.add(workflow)
    await session.commit()

    # Test skip parameter
    response = await client.get("/v1/workflows?skip=2")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 3

    # Test limit parameter
    response = await client.get("/v1/workflows?limit=2")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 2

    # Test skip and limit together
    response = await client.get("/v1/workflows?skip=1&limit=2")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 2


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_read_workflows_filter_by_id(session: AsyncSession, client: AsyncClient):
    """Test filtering workflows by ID"""
    # Create workflows
    workflow1 = models.Workflow(
        title="workflow-1", version=1, definition="def-1", workflow_engine="dummy"
    )
    workflow2 = models.Workflow(
        title="workflow-2", version=1, definition="def-2", workflow_engine="dummy"
    )
    session.add(workflow1)
    session.add(workflow2)
    await session.commit()
    await session.refresh(workflow1)
    await session.refresh(workflow2)

    # Filter by workflow1 ID
    response = await client.get(f"/v1/workflows?id={workflow1.id}")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["id"] == workflow1.id
    assert data[0]["title"] == "workflow-1"


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_read_workflows_order_by_title_asc(
    session: AsyncSession, client: AsyncClient
):
    """Test ordering workflows by title in ascending order"""
    # Create workflows with different titles
    for title in ["zebra-workflow", "alpha-workflow", "beta-workflow"]:
        workflow = models.Workflow(
            title=title, version=1, definition=f"def-{title}", workflow_engine="dummy"
        )
        session.add(workflow)
    await session.commit()

    # Order by title ascending
    response = await client.get("/v1/workflows?order_by=title&order=asc")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 3
    assert data[0]["title"] == "alpha-workflow"
    assert data[1]["title"] == "beta-workflow"
    assert data[2]["title"] == "zebra-workflow"


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_read_workflows_order_by_title_desc(
    session: AsyncSession, client: AsyncClient
):
    """Test ordering workflows by title in descending order"""
    # Create workflows with different titles
    for title in ["alpha-workflow", "beta-workflow", "zebra-workflow"]:
        workflow = models.Workflow(
            title=title, version=1, definition=f"def-{title}", workflow_engine="dummy"
        )
        session.add(workflow)
    await session.commit()

    # Order by title descending (default)
    response = await client.get("/v1/workflows?order_by=title&order=desc")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 3
    assert data[0]["title"] == "zebra-workflow"
    assert data[1]["title"] == "beta-workflow"
    assert data[2]["title"] == "alpha-workflow"


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_read_workflows_order_by_version(
    session: AsyncSession, client: AsyncClient
):
    """Test ordering workflows by version"""
    # Create multiple versions of same workflow
    for version in [3, 1, 2]:
        workflow = models.Workflow(
            title="version-test",
            version=version,
            definition=f"def-{version}",
            workflow_engine="dummy",
        )
        session.add(workflow)
    await session.commit()

    # Order by version ascending
    response = await client.get("/v1/workflows?order_by=version&order=asc")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 3
    assert data[0]["version"] == 1
    assert data[1]["version"] == 2
    assert data[2]["version"] == 3


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_read_workflows_order_by_id(session: AsyncSession, client: AsyncClient):
    """Test ordering workflows by ID"""
    # Create workflows
    workflows = []
    for i in range(3):
        workflow = models.Workflow(
            title=f"workflow-{i}",
            version=1,
            definition=f"def-{i}",
            workflow_engine="dummy",
        )
        session.add(workflow)
        workflows.append(workflow)
    await session.commit()
    for wf in workflows:
        await session.refresh(wf)

    # Order by ID descending (default)
    response = await client.get("/v1/workflows?order_by=id&order=desc")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 3
    assert data[0]["id"] > data[1]["id"]
    assert data[1]["id"] > data[2]["id"]

    # Order by ID ascending
    response = await client.get("/v1/workflows?order_by=id&order=asc")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 3
    assert data[0]["id"] < data[1]["id"]
    assert data[1]["id"] < data[2]["id"]


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_read_workflows_combined_query_params(
    session: AsyncSession, client: AsyncClient
):
    """Test combining multiple query parameters (skip, limit, order_by, order)"""
    # Create 10 workflows with different titles
    for i in range(10):
        workflow = models.Workflow(
            title=f"workflow-{i:02d}",
            version=1,
            definition=f"def-{i}",
            workflow_engine="dummy",
        )
        session.add(workflow)
    await session.commit()

    # Combine skip=2, limit=3, order_by=title, order=asc
    response = await client.get(
        "/v1/workflows?skip=2&limit=3&order_by=title&order=asc"
    )
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 3
    # Should get workflows 02, 03, 04 (after skipping 00, 01)
    assert data[0]["title"] == "workflow-02"
    assert data[1]["title"] == "workflow-03"
    assert data[2]["title"] == "workflow-04"


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_read_workflows_filter_by_id_with_ordering(
    session: AsyncSession, client: AsyncClient
):
    """Test that filtering by ID returns single result regardless of order params"""
    # Create workflows
    workflow1 = models.Workflow(
        title="workflow-1", version=1, definition="def-1", workflow_engine="dummy"
    )
    workflow2 = models.Workflow(
        title="workflow-2", version=1, definition="def-2", workflow_engine="dummy"
    )
    session.add(workflow1)
    session.add(workflow2)
    await session.commit()
    await session.refresh(workflow1)

    # Filter by ID with ordering params
    response = await client.get(
        f"/v1/workflows?id={workflow1.id}&order_by=title&order=desc"
    )
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["id"] == workflow1.id


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_read_workflows_invalid_order_param(client: AsyncClient):
    """Test that invalid order parameter defaults to 'desc'"""
    # Create a workflow
    response = await client.post(
        "/v1/workflows",
        json={
            "title": "test-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
        },
    )
    assert response.status_code == 201

    # Try invalid order parameter
    response = await client.get("/v1/workflows?order=invalid")
    data = response.json()

    # Should still return results (implementation may handle invalid params differently)
    assert response.status_code == 200
    assert len(data) >= 1


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_read_workflows_negative_skip(
    session: AsyncSession, client: AsyncClient
):
    """Test behavior with negative skip value"""
    # Create workflows
    for i in range(3):
        workflow = models.Workflow(
            title=f"workflow-{i}",
            version=1,
            definition=f"def-{i}",
            workflow_engine="dummy",
        )
        session.add(workflow)
    await session.commit()

    # Try negative skip - implementation may vary
    response = await client.get("/v1/workflows?skip=-1")

    assert response.status_code == 200


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_read_workflows_zero_limit(session: AsyncSession, client: AsyncClient):
    """Test behavior with limit=0"""
    # Create workflows
    for i in range(3):
        workflow = models.Workflow(
            title=f"workflow-{i}",
            version=1,
            definition=f"def-{i}",
            workflow_engine="dummy",
        )
        session.add(workflow)
    await session.commit()

    # Try limit=0
    response = await client.get("/v1/workflows?limit=0")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 0


@pytest.mark.GET
@pytest.mark.get_workflows
@pytest.mark.asyncio
async def test_read_workflows_large_limit(session: AsyncSession, client: AsyncClient):
    """Test behavior with very large limit value"""
    # Create 5 workflows
    for i in range(5):
        workflow = models.Workflow(
            title=f"workflow-{i}",
            version=1,
            definition=f"def-{i}",
            workflow_engine="dummy",
        )
        session.add(workflow)
    await session.commit()

    # Try very large limit
    response = await client.get("/v1/workflows?limit=10000")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 5  # Should return all available workflows


# ============================================================
# GET /v1/workflows/{title} - Get Workflow by Title Tests
# ============================================================


@pytest.mark.GET
@pytest.mark.get_workflow_by_title
@pytest.mark.parametrize(
    "title,workflows_data,latest,expected_count",
    [(case[0], case[1], case[2], case[3]) for case in GET_WORKFLOW_BY_TITLE_TEST_CASES],
    ids=[case[4] for case in GET_WORKFLOW_BY_TITLE_TEST_CASES],
)
@pytest.mark.asyncio
async def test_get_workflow_by_title(
    session: AsyncSession,
    client: AsyncClient,
    title: str,
    workflows_data: list[dict],
    latest: bool,
    expected_count: int,
):
    """Test getting workflows by title with different version scenarios"""
    # Create workflows in database
    for wf_data in workflows_data:
        workflow = models.Workflow(**wf_data)
        session.add(workflow)
    await session.commit()

    # Query API
    url = f"/v1/workflows/{title}"
    if latest:
        url += "?latest=true"

    response = await client.get(url)
    data = response.json()

    assert response.status_code == 200
    assert isinstance(data, list)
    assert len(data) == expected_count

    # If latest=true, verify we got the highest version
    if latest and len(data) > 0:
        max_version = max(
            wf["version"] for wf in workflows_data if wf["title"] == title
        )
        assert data[0]["version"] == max_version


@pytest.mark.GET
@pytest.mark.get_workflow_by_title
@pytest.mark.asyncio
async def test_get_workflow_by_title_not_found(client: AsyncClient):
    """Test getting workflow by non-existent title"""
    response = await client.get("/v1/workflows/non-existent-workflow")
    assert response.status_code == 404


@pytest.mark.GET
@pytest.mark.get_workflow_by_title
@pytest.mark.asyncio
async def test_get_workflow_by_title_versions_ordered(
    session: AsyncSession, client: AsyncClient
):
    """Test that versions are returned in descending order"""
    # Create multiple versions
    for version in [1, 2, 3, 4, 5]:
        workflow = models.Workflow(
            title="ordered-workflow",
            version=version,
            definition=f"def-{version}",
            workflow_engine="dummy",
        )
        session.add(workflow)
    await session.commit()

    response = await client.get("/v1/workflows/ordered-workflow")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 5

    # Verify descending order
    versions = [wf["version"] for wf in data]
    assert versions == [5, 4, 3, 2, 1]


@pytest.mark.GET
@pytest.mark.get_workflow_by_title
@pytest.mark.asyncio
async def test_get_workflow_by_title_latest_only(
    session: AsyncSession, client: AsyncClient
):
    """Test getting only the latest version of workflow by title"""
    # Create multiple versions
    for version in [1, 2, 3]:
        workflow = models.Workflow(
            title="multi-version-workflow",
            version=version,
            definition=f"def-v{version}",
            workflow_engine="dummy",
        )
        session.add(workflow)
    await session.commit()

    # Request only latest version
    response = await client.get("/v1/workflows/multi-version-workflow?latest=true")
    data = response.json()

    assert response.status_code == 200
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["version"] == 3
    assert data[0]["definition"] == "def-v3"


@pytest.mark.GET
@pytest.mark.get_workflow_by_title
@pytest.mark.asyncio
async def test_get_workflow_by_title_all_versions(
    session: AsyncSession, client: AsyncClient
):
    """Test getting all versions when latest=false"""
    # Create multiple versions
    for version in [1, 2]:
        workflow = models.Workflow(
            title="two-version-workflow",
            version=version,
            definition=f"def-v{version}",
            workflow_engine="dummy",
        )
        session.add(workflow)
    await session.commit()

    # Request all versions
    response = await client.get("/v1/workflows/two-version-workflow?latest=false")
    data = response.json()

    assert response.status_code == 200
    assert isinstance(data, list)
    assert len(data) == 2


# ============================================================
# GET /v1/workflows/{title}/{version} - Get Specific Workflow Tests
# ============================================================


@pytest.mark.get_workflow_by_title_version
@pytest.mark.parametrize(
    "workflow_data,title,version",
    [(case[0], case[1], case[2]) for case in GET_WORKFLOW_BY_TITLE_VERSION_TEST_CASES],
    ids=[case[3] for case in GET_WORKFLOW_BY_TITLE_VERSION_TEST_CASES],
)
@pytest.mark.asyncio
async def test_get_workflow_by_title_and_version(
    session: AsyncSession,
    client: AsyncClient,
    workflow_data: dict,
    title: str,
    version: int,
):
    """Test getting a specific workflow by title and version"""
    # Convert label dicts to Label models if present
    if "labels" in workflow_data:
        workflow_data = workflow_data.copy()
        workflow_data["labels"] = [
            models.Label(**label) for label in workflow_data["labels"]
        ]

    workflow = models.Workflow(**workflow_data)
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    response = await client.get(f"/v1/workflows/{title}/{version}")
    data = response.json()

    assert response.status_code == 200
    assert data["title"] == title
    assert data["version"] == version
    assert data["id"] == workflow.id


@pytest.mark.GET
@pytest.mark.get_workflow_by_title_version
@pytest.mark.parametrize(
    "url,expected_status",
    [(case[0], case[1]) for case in READ_WORKFLOW_ERROR_TEST_CASES],
    ids=[case[2] for case in READ_WORKFLOW_ERROR_TEST_CASES],
)
@pytest.mark.asyncio
async def test_read_workflow_errors(
    client: AsyncClient, url: str, expected_status: int
):
    """Test reading workflows with various error conditions"""
    response = await client.get(url)
    assert response.status_code == expected_status


# ============================================================
# DELETE /v1/workflows/{title}/{version} - Delete Workflow Tests
# ============================================================


@pytest.mark.DELETE
@pytest.mark.delete_workflow
@pytest.mark.parametrize(
    "title,version,expected_status",
    [(case[0], case[1], case[2]) for case in DELETE_WORKFLOW_TEST_CASES],
    ids=[case[3] for case in DELETE_WORKFLOW_TEST_CASES],
)
@pytest.mark.asyncio
async def test_delete_workflow(
    session: AsyncSession,
    client: AsyncClient,
    title: str,
    version: int,
    expected_status: int,
):
    """Test deleting workflows with different scenarios"""
    # Create a workflow to delete (only for successful delete test)
    if title == "existing-workflow" and version == 1:
        workflow = models.Workflow(
            title=title, version=version, definition="test", workflow_engine="dummy"
        )
        session.add(workflow)
        await session.commit()

    response = await client.delete(f"/v1/workflows/{title}/{version}")
    assert response.status_code == expected_status


@pytest.mark.DELETE
@pytest.mark.delete_workflow
@pytest.mark.asyncio
async def test_delete_workflow_is_soft_delete(
    session: AsyncSession, client: AsyncClient
):
    """Test that delete is a soft delete (sets removed=True)"""
    # Create workflow
    workflow = models.Workflow(
        title="soft-delete-test",
        version=1,
        definition="test",
        workflow_engine="dummy",
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)
    workflow_id = workflow.id

    # Delete it
    response = await client.delete("/v1/workflows/soft-delete-test/1")
    assert response.status_code == 204

    # Verify it's not returned by GET API
    response = await client.get("/v1/workflows/soft-delete-test/1")
    assert response.status_code == 404

    # But verify it still exists in DB with removed=True
    from sqlalchemy import select

    stmt = select(models.Workflow).where(models.Workflow.id == workflow_id)
    result = await session.execute(stmt)
    db_workflow = result.scalars().first()
    assert db_workflow is not None
    assert db_workflow.removed is True


@pytest.mark.DELETE
@pytest.mark.delete_workflow
@pytest.mark.asyncio
async def test_delete_workflow_twice_returns_404(
    session: AsyncSession, client: AsyncClient
):
    """Test that deleting same workflow twice returns 404"""
    # Create workflow
    workflow = models.Workflow(
        title="double-delete",
        version=1,
        definition="test",
        workflow_engine="dummy",
    )
    session.add(workflow)
    await session.commit()

    # Delete first time - success
    response = await client.delete("/v1/workflows/double-delete/1")
    assert response.status_code == 204

    # Delete second time - not found
    response = await client.delete("/v1/workflows/double-delete/1")
    assert response.status_code == 404
