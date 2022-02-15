from typing import Optional, List
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, Response, File, Header
from sqlalchemy.orm import Session
from urllib.parse import urlparse
import requests
import httpx
import json
import asyncio


from app import models
from app.dependencies import get_db
from app import schemas
from app import crud
from app.utils import get_dag_list, get_dataset_list, execute_workflow, raise_kaapana_connection_error


router = APIRouter()


@router.post("/remote-kaapana-instance", response_model=schemas.KaapanaInstance)
async def create_remote_kaapana_instance(remote_kaapana_instance: schemas.RemoteKaapanaInstanceCreate, db: Session = Depends(get_db)):
    return crud.create_remote_kaapana_instance(db=db, remote_kaapana_instance=remote_kaapana_instance)

@router.post("/client-kaapana-instance", response_model=schemas.KaapanaInstance)
async def create_client_kaapana_instance(client_kaapana_instance: schemas.ClientKaapanaInstanceCreate, db: Session = Depends(get_db)):
    return crud.create_client_kaapana_instance(db=db, client_kaapana_instance=client_kaapana_instance)

@router.get("/remote-kaapana-instance", response_model=schemas.KaapanaInstanceWithJob)
async def get_remote_kaapana_instance(node_id: str, db: Session = Depends(get_db)):
    return crud.get_kaapana_instance(db, node_id, remote=True)

@router.get("/client-kaapana-instance", response_model=schemas.KaapanaInstanceWithJob)
async def get_client_kaapana_instance(db: Session = Depends(get_db)):
    # url = urlparse(str(request.url))
    return crud.get_kaapana_instance(db, remote=False)

@router.get("/remote-kaapana-instances", response_model=List[schemas.KaapanaInstanceWithJob])
async def get_remote_kaapana_instances(db: Session = Depends(get_db)):
    return crud.get_kaapana_instances(db)

@router.delete("/kaapana-instance")
async def delete_kaapana_instance(kaapana_instance_id: int, db: Session = Depends(get_db)):
    return crud.delete_kaapana_instance(db, kaapana_instance_id=kaapana_instance_id)

@router.delete("/kaapana-instances")
async def delete_kaapana_instances( db: Session = Depends(get_db)):
    return crud.delete_kaapana_instances(db)

@router.post("/job", response_model=schemas.Job)
async def create_job(job: schemas.JobCreate, db: Session = Depends(get_db)):
    return crud.create_job(db=db, job=job)

@router.get("/job", response_model=schemas.Job)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    return crud.get_job(db, job_id, remote=False)

@router.get("/jobs", response_model=List[schemas.Job])
async def get_jobs(node_id: str = None, status: str = None, db: Session = Depends(get_db)):
    return crud.get_jobs(db, node_id, status, remote=False)

@router.put("/job", response_model=schemas.Job)
async def put_job(job_id: int, status: str, db: Session = Depends(get_db)):
    return crud.update_job(db, job_id, status, remote=False)

@router.delete("/job")
async def delete_job(job_id: int, db: Session = Depends(get_db)):
    return crud.delete_job(db, job_id, remote=False)

@router.delete("/jobs")
async def delete_jobs(db: Session = Depends(get_db)):
    return crud.delete_jobs(db)

@router.get("/dags")
async def dags():
    return get_dag_list()

@router.get("/datasets")
async def datasets():
    return get_dataset_list()

@router.get("/check-for-remote-updates", response_model=List[schemas.Job])
async def check_for_remote_updates(db: Session = Depends(get_db)):
    pending_jobs = []
    print(100*'#')
    db_client_kaapana = crud.get_kaapana_instance(db, remote=False)
    if db_client_kaapana.automatic_job_execution is True:
        client_status = "scheduled"
        remote_status = "scheduled"
        print('scheduled')
    else:
        client_status = "pending"
        remote_status = "pending"
    db_remote_kaapana_instances = crud.get_kaapana_instances(db, remote=True)
    for db_remote_kaapana_instance in db_remote_kaapana_instances:
        remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/federated-backend/remote'
        print(100*'#')
        print(remote_backend_url)
        async with httpx.AsyncClient(verify=db_remote_kaapana_instance.ssl_check) as client:
            r = await client.get(f'{remote_backend_url}/jobs', params={
                "node_id": db_remote_kaapana_instance.node_id,
                "status": "queued",
            }, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
            raise_kaapana_connection_error(r)
            incoming_jobs =  r.json()
            print(len(incoming_jobs))
            # print(incoming_jobs)
        for incoming_job in incoming_jobs:
            async with httpx.AsyncClient(verify=db_remote_kaapana_instance.ssl_check) as client:
                r = await client.put(f'{remote_backend_url}/job', params={
                    "job_id": incoming_job['id'],
                    "status": remote_status
                }, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
                raise_kaapana_connection_error(r)
                # print(r.json())
            incoming_job['kaapana_instance_id'] = db_client_kaapana.id
            incoming_job['remote_id'] = incoming_job["id"]
            incoming_job['status'] = client_status
            job = schemas.JobCreate(**incoming_job)
            db_job = crud.create_job(db, job)
            pending_jobs.append(db_job)
        # # request for remote
        # for job in db_remote_kaapana_instance.jobs:
        #     if job.status == 'pending':
        #         # Todo
        #         # get_job

        #         print('Executing')
        #         try:
        #             execute_workflow(db_client_kaapana, job.conf_data, job.dry_run)
        #             crud.update_job(db, job.id, 'running')
        #         except:
        #             raise HTTPException(status_code=500, detail="Your job could not be executed successfully")

    return pending_jobs


@router.get("/execute-scheduled-jobs", response_model=List[schemas.Job])
async def execute_scheduled_jobs(db: Session = Depends(get_db)):
    executed_scheduled_jobs = []
    db_client_kaapana = crud.get_kaapana_instance(db, remote=False)
    for db_job in db_client_kaapana.jobs:
        if db_job.status == 'scheduled':
            print('Executing', db_job.conf_data, db_job.dry_run)
            conf_data = json.loads(db_job.conf_data)
            conf_data['conf']['federated']['client_job_id'] = db_job.id
            conf_data['conf']['federated']['remote_job_id'] = db_job.remote_id
            resp = execute_workflow(db_client_kaapana, conf_data, db_job.dry_run)
            executed_scheduled_jobs.append(db_job)
            if resp == 'dry_run':
                return Response(f"The configuration for the allowed dags and datasets is okay!", 200)
            # crud.update_job(db, job.id, 'running', remote=False)
            # print('huhu')
            # db_remote_kaapana_instance = crud.get_kaapana_instance(db, node_id=conf_data['conf']['federated']['node_id'], remote=True)
            # remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/federated-backend/remote'
            # async with httpx.AsyncClient(verify=db_remote_kaapana_instance.ssl_check) as client:
            #     r = await client.put(f'{remote_backend_url}/job', params={
            #         "job_id": job.remote_id,
            #         "status": "running"
            #     }, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
            #     raise_kaapana_connection_error(r)
            #     print(r.json())
                    
    return executed_scheduled_jobs

