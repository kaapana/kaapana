import requests
import json
from fastapi import APIRouter, UploadFile, Response, File, Header, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db

from app import models
from app.utils import json_loads_client_network, get_dataset_list, get_dataset_list


router = APIRouter()


@router.get("/health-check")
async def health_check():
    return {f"Federated backend is up and running!"}


@router.post("/trigger-workflow")
async def trigger_workflow(data: dict, dry_run: str = True,  db: Session = Depends(get_db)):
    db_client_network = db.query(models.ClientNetwork).first()
    db_client_network = json_loads_client_network(db_client_network)
    if data['conf']['dag'] not in db_client_network.allowed_dags:
        raise HTTPException(status_code=403, detail=f"Dag {data['conf']['dag']} is not allowed to be triggered from remote!")
    queried_data = get_dataset_list({'query': data['conf']['query']})
    if not all([bool(set(d) & set(db_client_network.allowed_datasets)) for d in queried_data]):
        raise HTTPException(status_code=403, detail = f"Your query outputed data with the tags: " \
            f"{''.join(sorted(list(set([d for datasets in queried_data for d in datasets]))))}, " \
            f"but only the following tags are allowed to be used from remote: {','.join(db_client_network.allowed_datasets)} !")
    
    if dry_run.lower() == 'true':
        return Response(f"The configuration for the allowed dags and datasets is okay!", 200)
        
    resp = requests.post('http://airflow-service.flow.svc:8080/flow/kaapana/api/trigger/meta-trigger',  json=data)
    # excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    # headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    # response = Response(resp.content, resp.status_code, headers)
    return Response(content=resp.content, status_code= resp.status_code)


@router.get("/minio-presigned-url")
async def minio_presigned_url(presigned_url: str = Header(...)):
    print(f'http://minio-service.store.svc:9000{presigned_url}')
    resp = requests.get(f'http://minio-service.store.svc:9000{presigned_url}')
    # excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    # headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    return Response(resp.content, resp.status_code)


@router.post("/minio-presigned-url")
def minio_presigned_url(file: UploadFile = File(...), presigned_url: str = Header(...)):
    resp = requests.put(f'http://minio-service.store.svc:9000{presigned_url}', data=file.file)
    # excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    # headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    # print(resp)
    response = Response(resp.content, resp.status_code)
    return response