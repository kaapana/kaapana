import os
from fastapi import Header, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from minio import Minio
from opensearchpy import OpenSearch
from .monitoring.services import MonitoringService
from .users.services import UserService

# from .workflows.services import WorkflowService
from .workflows.models import KaapanaInstance
from .config import settings
from .database import SessionLocal
from .workflows.utils import HelperMinio


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_monitoring_service(request: Request) -> MonitoringService:
    x_auth_token = request.headers.get("x-forwarded-access-token")
    os_host = f"opensearch-service.{settings.services_namespace}.svc"
    os_port = "9200"
    auth_headers = {"Authorization": f"Bearer {x_auth_token}"}
    opensearchClient = OpenSearch(
        hosts=[{"host": os_host, "port": os_port}],
        http_compress=True,  # enables gzip compression for request bodies
        use_ssl=True,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        timeout=10,
        headers=auth_headers,
    )

    yield MonitoringService(
        prometheus_url=settings.prometheus_url, opensearchClient=opensearchClient
    )


def get_user_service() -> UserService:
    yield UserService(
        settings.keycloak_url,
        settings.keycloak_admin_username,
        settings.keycloak_admin_password,
    )


def get_minio(request: Request) -> HelperMinio:
    x_auth_token = request.headers.get("x-forwarded-access-token")
    yield HelperMinio(x_auth_token)


def get_opensearch(request: Request):
    x_auth_token = request.headers.get("x-forwarded-access-token")
    os_host = f"opensearch-service.{settings.services_namespace}.svc"
    os_port = "9200"
    auth_headers = {"Authorization": f"Bearer {x_auth_token}"}
    yield OpenSearch(
        hosts=[{"host": os_host, "port": os_port}],
        http_compress=True,  # enables gzip compression for request bodies
        use_ssl=True,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        timeout=10,
        headers=auth_headers,
        # ca_certs = ca_certs_path
    )


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
