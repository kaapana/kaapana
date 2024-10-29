import traceback

from app import crud
from app.database import get_session_non_context_manager as get_session
from app.kube import (
    create_k8s_secret,
    delete_k8s_secret,
    get_k8s_secret,
    hash_secret_name,
)
from app.logger import get_logger
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = get_logger(__file__)


# TODO gcloud specific
class SecretData(BaseModel):
    type: str
    project_id: str
    private_key_id: str
    private_key: str
    client_email: str
    client_id: str
    auth_uri: str
    token_uri: str
    auth_provider_x509_cert_url: str
    client_x509_cert_url: str
    universe_domain: str


class Endpoint(BaseModel):
    endpoint: str


class RequestData(BaseModel):
    endpoint: str
    secret_data: SecretData


@router.head("/endpoints")
async def read_endpoints() -> dict:
    """
    Health check endpoint to verify if the DICOM web multiplexer service is responsive.

    Returns:
        dict: Success Response.
    """
    return Response(status_code=200)


@router.get("/endpoints")
async def retrieve_all_endpoints(session: AsyncSession = Depends(get_session)):
    """
    Retrieve all endpoints.

    Args:
        session (AsyncSession): Database session dependency.

    Returns:
        list: List of endpoints.
    """
    endpoints = await crud.get_endpoints(session)
    return endpoints


@router.post("/endpoints")
async def create_endpoint(
    data: RequestData, session: AsyncSession = Depends(get_session)
) -> Response:
    """
    Create a specific endpoint in Kubernetes secret and database.

    Args:
        data (RequestData): Request data containing endpoint and credentials.
        session (AsyncSession): Database session dependency.

    Returns:
        Response: Success or error response.
    """
    endpoint = data.endpoint
    secret_data = data.secret_data.model_dump()

    try:
        secret_name = hash_secret_name(endpoint)
        if not create_k8s_secret(secret_name, secret_data):
            return Response(
                status_code=500, content="Unable to create secret for the endpoint"
            )

        if not await crud.add_endpoint(endpoint, session):
            return Response(
                status_code=500, content="Unable to create database entry for the endpoint"
            )
        
        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Error creating endpoint: {e}")
        logger.debug(traceback.format_exc())
        return Response(status_code=500, content="Unable to create endpoint")


@router.delete("/endpoints")
async def delete_endpoint(
    endpoint: Endpoint, session: AsyncSession = Depends(get_session)
):
    """
    Delete a specific endpoint from Kubernetes secret and from database.

    Args:
        endpoint (Endpoint): Endpoint data containing endpoint name.
        session (AsyncSession): Database session dependency.

    Returns:
        Response: Success or error response.
    """
    try:
        endpoint = endpoint.endpoint
        secret_name = hash_secret_name(endpoint)

        if not delete_k8s_secret(secret_name):
            return Response(status_code=500, content=f"Couldn't delete secret for endpoint {endpoint}.")

        logger.info(f"Deleted secret for endpoint {endpoint}.")
        if not await crud.remove_endpoint(endpoint, session):
            return Response(status_code=500, content=f"Couldn't remove database entry for endpoint {endpoint}.")
        return Response(status_code=200)

    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return Response(status_code=500, content="Unable to delete endpoint")


@router.get("/endpoints/{endpoint}")
async def retrieve_endpoint(endpoint: str) -> dict:
    """
    Retrieve a specific endpoint secret by name.

    Args:
        endpoint (str): The endpoint name.

    Returns:
        dict: Endpoint details with associated secret data.
    """
    try:
        secret_name = hash_secret_name(endpoint)
        secret_data = get_k8s_secret(secret_name)

        if not secret_data:
            return Response(status_code=404, detail="Endpoint secret not found.")
        return {"endpoint": endpoint, "secret_data": secret_data}

    except Exception as e:
        logger.error(f"Error retrieving endpoint: {e}")
        logger.debug(traceback.format_exc())
        raise Response(status_code=500, detail="Error retrieving endpoint")