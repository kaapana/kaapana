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
from fastapi import APIRouter, Depends, HTTPException, Response
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
async def read_endpoints():
    return {"message": "dicom-web-multiplexer is alive."}


@router.get("/endpoints")
async def retrieve_all_endpoints(session: AsyncSession = Depends(get_session)):
    """Retrieve all endpoints containing credentials."""
    endpoints = await crud.get_endpoints(session)
    return endpoints


@router.post("/endpoints")
async def create_endpoint(
    data: RequestData, session: AsyncSession = Depends(get_session)
):
    """Create a new endpoint secret."""

    endpoint = data.endpoint
    secret_data = data.secret_data.model_dump()

    try:
        secret_name = hash_secret_name(endpoint)
        if not create_k8s_secret(secret_name, secret_data):
            return Response(
                status_code=500, content="Unable to create secret for the endpoint"
            )
        try:
            await crud.add_endpoint(endpoint, session)
            logger.info(f"Created new secret for endpoint.")
            return Response(status_code=200)
        except Exception:
            # TODO
            return Response(status_code=200)

    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return Response(status_code=500, content="Unable to save endpoint")


@router.delete("/endpoints")
async def delete_endpoint(
    endpoint: Endpoint, session: AsyncSession = Depends(get_session)
):
    """Delete a specific endpoint secret."""
    try:
        endpoint = endpoint.endpoint
        secret_name = hash_secret_name(endpoint)

        # Delete the secret
        if not delete_k8s_secret(secret_name):
            logger.warning(f"Couldn't delete secret for endpoint {endpoint}.")
            return Response(status_code=500)

        logger.info(f"Deleted secret for endpoint {endpoint}.")

        await crud.remove_endpoint(endpoint, session)
        return Response(status_code=200)

    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return Response(status_code=500)


@router.get("/endpoints")
async def retrieve_endpoint(endpoint: Endpoint):
    """Retrieve a specific endpoint secret by name."""
    try:
        endpoint = endpoint.endpoint
        secret_name = hash_secret_name(endpoint)
        secret_data = get_k8s_secret(secret_name)

        if not secret_data:
            logger.warning(f"Secret for endpoint {endpoint} not found.")
            raise HTTPException(status_code=404, detail="Endpoint not found.")

        return {"endpoint": endpoint, "secret_data": secret_data}

    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        Response(status_code=500)
