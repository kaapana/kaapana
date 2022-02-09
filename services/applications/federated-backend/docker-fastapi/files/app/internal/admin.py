import requests
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, Response, File, Header
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app import schemas
from app import crud
from app.utils import get_dag_list, get_dataset_list


router = APIRouter()


@router.get("/")
async def root(request: Request):
    return {"message": "Hello World updating", "root_path": request.scope.get("root_path")}

@router.post("/remote-network", response_model=schemas.RemoteNetwork)
def create_remote_network(remote_network: schemas.RemoteNetworkCreate, db: Session = Depends(get_db)):
    return crud.create_remote_network(db=db, remote_network=remote_network)


@router.get("/remote-network", response_model=schemas.RemoteNetwork)
def get_remote_network(db: Session = Depends(get_db)):
    return crud.get_remote_network(db)


@router.post("/client-network", response_model=schemas.ClientNetwork)
def create_client_network(request: Request, client_network: schemas.ClientNetworkCreate, db: Session = Depends(get_db)):
    return crud.create_client_network(db=db, client_network=client_network, request=request)


@router.get("/client-network", response_model=schemas.ClientNetwork)
def get_client_network(db: Session = Depends(get_db)):
    return crud.get_client_network(db)

@router.get("/dags")
def dags():
    return get_dag_list()

@router.get("/datasets")
def datasets():
    return get_dataset_list()