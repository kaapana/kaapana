from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from .config import settings
from app.services.workflow import WorkflowService

from .database import SessionLocal

from . import models


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_workflow_service() -> WorkflowService:
    yield WorkflowService(airflow_api=settings.airflow_url)


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

