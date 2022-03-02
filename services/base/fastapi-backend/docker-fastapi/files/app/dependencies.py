import os
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.extensions import ExtensionService
from app.services.monitoring import MonitoringService
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

