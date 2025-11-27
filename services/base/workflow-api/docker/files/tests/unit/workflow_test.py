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
- GET /v1/workflows/{title}/{version}/tasks
- GET /v1/workflows/{title}/{version}/tasks/{task_title}
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
