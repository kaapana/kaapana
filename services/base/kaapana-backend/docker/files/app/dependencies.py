import json

import httpx
import jwt
import requests
from fastapi import Depends, Header, HTTPException, Request
from kaapanapy.helper import get_opensearch_client
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal
from .monitoring.services import MonitoringService
from .users.services import UserService
from .workflows.models import KaapanaInstance
from .workflows.utils import HelperMinio


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_monitoring_service() -> MonitoringService:
    yield MonitoringService(prometheus_url=settings.prometheus_url)


def get_user_service() -> UserService:
    yield UserService(
        settings.keycloak_url,
        settings.keycloak_admin_username,
        settings.keycloak_admin_password,
    )


def get_minio(request: Request) -> HelperMinio:
    x_auth_token = request.headers.get("x-forwarded-access-token")
    yield HelperMinio(x_auth_token)


# def get_workflow_service() -> WorkflowService:
#     yield WorkflowService(airflow_api=settings.airflow_url)


async def get_token_header(
    FederatedAuthorization: str = Header(...), db: Session = Depends(get_db)
):
    if FederatedAuthorization:
        db_client_kaapana_instance = (
            db.query(KaapanaInstance).filter_by(token=FederatedAuthorization).first()
        )
        if db_client_kaapana_instance:
            return db_client_kaapana_instance
        else:
            raise HTTPException(
                status_code=400, detail="FederatedAuthorization header invalid"
            )


async def get_query_token(token: str):
    if token != "jessica":
        raise HTTPException(status_code=400, detail="No Jessica token provided")


def get_opensearch(request: Request):
    x_auth_token = request.headers.get("x-forwarded-access-token")
    yield get_opensearch_client(access_token=x_auth_token)


def get_project(request: Request):
    project = request.headers.get("Project")
    if not project:
        return None
    try:
        return json.loads(project)
    except json.JSONDecodeError:
        return None


def get_project_index(project=Depends(get_project)):
    return project.get("opensearch_index")


def get_allowed_software(project=Depends(get_project)) -> list:
    project_id = project.get("id")
    enabled_software_in_project = httpx.get(
        f"http://aii-service.services.svc:8080/projects/{project_id}/software-mappings"
    ).json()
    return [software.get("software_uuid") for software in enabled_software_in_project]


def get_access_token(request: Request):
    access_token = request.headers.get("x-forwarded-access-token", None)
    if access_token is None:
        decoded_access_token = {}
    else:
        decoded_access_token = jwt.decode(
            access_token, options={"verify_signature": False}
        )
    return decoded_access_token


def get_dcmweb_helper(request: Request):
    return HelperDcmWeb()


def fetch_default_project_id() -> str:
    response = requests.get("http://aii-service.services.svc:8080/projects/admin")
    response.raise_for_status()
    return response.json().get("id")
