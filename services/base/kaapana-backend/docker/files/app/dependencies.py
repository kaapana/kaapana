import os
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from minio import Minio
from .extensions.services import ExtensionService
from .monitoring.services import MonitoringService
from .users.services import UserService
from .workflows.services import WorkflowService
from .experiments.models import KaapanaInstance
from .config import settings
from .database import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_monitoring_service() -> MonitoringService:
    yield MonitoringService(prometheus_url=settings.prometheus_url)

def get_extension_service() -> ExtensionService:
    yield ExtensionService(helm_api=settings.kube_helm_url)

def get_user_service() -> UserService:
    yield UserService(settings.keycloak_url, settings.keycloak_admin_username, settings.keycloak_admin_password)

def get_minio() -> Minio:
    yield  Minio(settings.minio_url, access_key=settings.minio_username, secret_key=settings.minio_password, secure=False)

def get_workflow_service() -> WorkflowService:
    yield WorkflowService(airflow_api=settings.airflow_url)

async def get_token_header(FederatedAuthorization: str = Header(...), db: Session = Depends(get_db)):
    if FederatedAuthorization:
        db_client_kaapana_instance = db.query(KaapanaInstance).filter_by(token=FederatedAuthorization).first()
        if db_client_kaapana_instance:
            return db_client_kaapana_instance
        else:
            raise HTTPException(status_code=400, detail="FederatedAuthorization header invalid")

async def get_query_token(token: str):
    if token != "jessica":
        raise HTTPException(status_code=400, detail="No Jessica token provided")

