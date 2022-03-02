import os
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from minio import Minio
from app.services.extensions import ExtensionService
from app.services.monitoring import MonitoringService
from app.services.users import UserService
from .config import settings
from .database import SessionLocal
from . import models


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_monitoring_service() -> MonitoringService:
    client = MonitoringService(prometheus_url=settings.prometheus_url)
    yield client

def get_extension_service() -> ExtensionService:
    yield ExtensionService(helm_api=settings.kube_helm_url)

def get_user_service() -> UserService:
    yield UserService(settings.keycloak_url, settings.keycloak_user, settings.keycloak_password)

def get_minio() -> Minio:
    yield  Minio(settings.minio_url, access_key=settings.minio_access_key, secret_key=settings.minio_secret_key, secure=False)

async def get_token_header(FederatedAuthorization: str = Header(...), db: Session = Depends(get_db)):
    if FederatedAuthorization:
        db_client_kaapana_instance = db.query(models.KaapanaInstance).filter_by(token=FederatedAuthorization).first()
        if db_client_kaapana_instance:
            return db_client_kaapana_instance
        else:
            raise HTTPException(status_code=400, detail="FederatedAuthorization header invalid")


async def get_query_token(token: str):
    if token != "jessica":
        raise HTTPException(status_code=400, detail="No Jessica token provided")

