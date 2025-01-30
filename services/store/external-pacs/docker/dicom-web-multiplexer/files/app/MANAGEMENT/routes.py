import traceback
from typing import List

from app.crud import (
    get_all_datasources,
    add_datasource,
    get_datasource,
    remove_datasource,
)
from app.models import (
    DataSourceDB,
    DataSourceResponse,
    AuthenticatedDataSourceRequest,
    AuthenticatedDataSourceResponse,
    DataSourceRequest,
)
from app.database import get_session_non_context_manager as get_session
from app.kube import (
    create_k8s_secret,
    delete_k8s_secret,
    get_k8s_secret,
    hash_secret_name,
)
from app.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = get_logger(__file__)


@router.head("/alive")
async def read_multiplexer() -> Response:
    """
    Health check endpoint to verify if the DICOM web multiplexer service is responsive.

    Returns:
        Response: Success Response.
    """
    return Response(status_code=200)


@router.get("/datasources")
async def retrieve_datasources(
    project_index: str = Query(None),
    session: AsyncSession = Depends(get_session),
) -> List[DataSourceResponse]:
    """
    Retrieve all datasources, optionally filtered by project_index.

    Args:
        project_index (str): Optional filter for datasources by project_index.
        session (AsyncSession): Database session dependency.

    Returns:
        List[DataSourceAPI]: List of transformed datasource objects.
    """
    datasources = await get_all_datasources(project_index, session)

    return [DataSourceResponse.model_validate(ds) for ds in datasources]


@router.post("/datasources")
async def create_datasource(
    datasource: AuthenticatedDataSourceRequest,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """
    Create a datasource in Kubernetes secret and database.

    Args:
        data (DataSourceRequest): Request data containing datasource and credentials.
        session (AsyncSession): Database session dependency.

    Returns:
        Response: Success or error response.
    """
    secret_data = datasource.secret_data.model_dump()
    datasource = datasource.datasource

    secret_name = hash_secret_name(datasource.dcmweb_endpoint)
    if not create_k8s_secret(secret_name, secret_data):
        return Response(
            status_code=500,
            content=f"Unable to create secret for the datasource {datasource}",
        )
    datasource_db = DataSourceDB(
        dcmweb_endpoint=datasource.dcmweb_endpoint,
        project_index=datasource.project_index,
    )
    await add_datasource(datasource_db, session)
    return Response(status_code=200)


@router.delete("/datasources")
async def delete_datasource(
    datasource: DataSourceRequest,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """
    Delete a specific datasource from Kubernetes secret and database.

    Args:
        endpoint (str): The endpoint of the datasource to delete.
        project_index (str): The project_index of the datasource to delete.
        session (AsyncSession): Database session dependency.

    Returns:
        Response: Success or error response.
    """
    secret_name = hash_secret_name(datasource.dcmweb_endpoint)

    if not delete_k8s_secret(secret_name):
        return Response(
            status_code=500,
            content=f"Couldn't delete secret for datasource {datasource}.",
        )
    datasource_db = DataSourceDB(
        dcmweb_endpoint=datasource.dcmweb_endpoint,
        project_index=datasource.project_index,
    )
    await remove_datasource(datasource_db, session)
    return Response(status_code=200)


@router.get("/datasource")
async def retrieve_datasource(
    datasource: DataSourceRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Retrieve a specific datasource secret and details by endpoint and project_index.

    Args:
        endpoint (str): The endpoint of the datasource.
        project_index (str): The project_index of the datasource.
        session (AsyncSession): Database session dependency.

    Returns:
        dict: Datasource details with associated secret data.
    """

    datasource_db = await get_datasource(datasource, session)
    datasource = DataSourceResponse.model_validate(datasource_db)
    if not datasource:
        raise HTTPException(
            status_code=404, detail=f"Datasource not found: {datasource}."
        )

    secret_name = hash_secret_name(datasource.dcmweb_endpoint)
    secret_data = get_k8s_secret(secret_name)

    if not secret_data:
        raise HTTPException(
            status_code=404, detail=f"Datasource secret not found: {datasource}."
        )

    return AuthenticatedDataSourceResponse(
        datasource=datasource, secret_data=secret_data
    )
