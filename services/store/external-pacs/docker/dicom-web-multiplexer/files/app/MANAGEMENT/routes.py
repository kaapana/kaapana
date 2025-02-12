
from app.models import (
    AuthenticatedDataSourceRequest,
    AuthenticatedDataSourceResponse,
    DataSourceRequest,
)
from app.kube import (
    create_k8s_secret,
    delete_k8s_secret,
    get_k8s_secret,
    hash_secret_name,
)
from app.logger import get_logger
from fastapi import APIRouter, HTTPException, Response

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

@router.post("/datasources")
async def create_datasource(
    datasource: AuthenticatedDataSourceRequest,
) -> Response:
    """
    Create a datasource in Kubernetes secret and the database.

    Args:
        datasource (AuthenticatedDataSourceRequest): Request data containing datasource and credentials.
        session (AsyncSession): Database session dependency.

    Returns:
        Response: Success (200) or error (500) response.
    """
    secret_data = datasource.secret_data.model_dump()
    datasource = datasource.datasource

    secret_name = hash_secret_name(datasource.dcmweb_endpoint)
    if not create_k8s_secret(secret_name, secret_data):
        return Response(
            status_code=500,
            content=f"Unable to create secret for the datasource {datasource}",
        )
    return Response(status_code=200)


@router.delete("/datasources")
async def delete_datasource(
    datasource: DataSourceRequest,
) -> Response:
    """
    Delete a specific datasource from Kubernetes secret and the database.

    Args:
        datasource (DataSourceRequest): The datasource object containing endpoint and project_index to delete.
        session (AsyncSession): Database session dependency.

    Returns:
        Response: Success (200) or error (500) response.
    """
    secret_name = hash_secret_name(datasource.dcmweb_endpoint)

    if not delete_k8s_secret(secret_name):
        return Response(
            status_code=500,
            content=f"Couldn't delete secret for datasource {datasource}.",
        )
    return Response(status_code=200)


@router.get("/datasource")
async def retrieve_datasource(
    datasource: DataSourceRequest,

):
    """
    Retrieve a specific datasource and its associated secret data.

    Args:
        datasource (DataSourceRequest): The datasource object containing endpoint and project_index.
        session (AsyncSession): Database session dependency.

    Returns:
        AuthenticatedDataSourceResponse: Datasource details with associated secret data.

    Raises:
        HTTPException: If the datasource or its secret data is not found.
    """
    secret_name = hash_secret_name(datasource.dcmweb_endpoint)
    secret_data = get_k8s_secret(secret_name)

    if not secret_data:
        raise HTTPException(
            status_code=404, detail=f"Datasource secret not found: {datasource}."
        )

    return AuthenticatedDataSourceResponse(
        datasource=datasource, secret_data=secret_data
    )
