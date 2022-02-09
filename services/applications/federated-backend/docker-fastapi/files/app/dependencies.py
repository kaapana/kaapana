from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from .database import SessionLocal

from . import models


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_token_header(FederatedAuthorization: str = Header(...), db: Session = Depends(get_db)):
    if FederatedAuthorization:
        db_client_network = db.query(models.ClientNetwork).filter_by(token=FederatedAuthorization).first()
        print(db_client_network)
        if db_client_network:
            return db_client_network
        else:
            raise HTTPException(status_code=400, detail="FederatedAuthorization header invalid")


async def get_query_token(token: str):
    if token != "jessica":
        raise HTTPException(status_code=400, detail="No Jessica token provided")

