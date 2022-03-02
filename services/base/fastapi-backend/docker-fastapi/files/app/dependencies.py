import os
from datetime import datetime
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from prometheus_api_client import PrometheusConnect
from app.services.extensions import ExtensionService
from typing import List
from .config import settings
from .database import SessionLocal
from . import models


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class PrometheusClient:
    def __init__(self):
        url = os.getenv('PROMETHEUS_URL')
        if not url:
            print("No prometheus url is given")
        else:
            self.con = PrometheusConnect(url)

    def query(self, name: str, q: str):
        result = self.con.custom_query(query=q)
        if not result:
            return None
        return {
            'metric': name,
            'value': float(result[0]['value'][1]),
            'timestamp': datetime.fromtimestamp(result[0]['value'][0])
        }

    def all_metrics(self) -> List[str]:
        return self.con.all_metrics()

def get_prometheus_client() -> PrometheusClient:
    client = PrometheusClient()
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

