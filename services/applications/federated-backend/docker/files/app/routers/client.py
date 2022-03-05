from typing import Optional, List
import requests
import httpx
import json
import copy


from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, Response, File, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from urllib.parse import urlparse
from fastapi.encoders import jsonable_encoder
import asyncio


from app import models
from app.dependencies import get_db
from app import schemas
from app import crud
from app.utils import get_dag_list, get_dataset_list, raise_kaapana_connection_error, get_remote_updates, NODE_ID


router = APIRouter()

@router.post("/remote-kaapana-instance", response_model=schemas.KaapanaInstance)
async def create_remote_kaapana_instance(remote_kaapana_instance: schemas.RemoteKaapanaInstanceCreate, db: Session = Depends(get_db)):
    return crud.create_and_update_remote_kaapana_instance(db=db, remote_kaapana_instance=remote_kaapana_instance)

@router.post("/client-kaapana-instance", response_model=schemas.KaapanaInstance)
async def create_client_kaapana_instance(client_kaapana_instance: schemas.ClientKaapanaInstanceCreate, db: Session = Depends(get_db)):
    return crud.create_and_update_client_kaapana_instance(db=db, client_kaapana_instance=client_kaapana_instance)

@router.put("/remote-kaapana-instance", response_model=schemas.KaapanaInstance)
async def put_remote_kaapana_instance(remote_kaapana_instance: schemas.RemoteKaapanaInstanceCreate, db: Session = Depends(get_db)):
    return crud.create_and_update_remote_kaapana_instance(db=db, remote_kaapana_instance=remote_kaapana_instance, action='update')

@router.put("/client-kaapana-instance", response_model=schemas.KaapanaInstance)
async def put_client_kaapana_instance(client_kaapana_instance: schemas.ClientKaapanaInstanceCreate, db: Session = Depends(get_db)):
    return crud.create_and_update_client_kaapana_instance(db=db, client_kaapana_instance=client_kaapana_instance, action='update')

@router.get("/remote-kaapana-instance", response_model=schemas.KaapanaInstanceWithJobs)
async def get_remote_kaapana_instance(node_id: str, db: Session = Depends(get_db)):
    return crud.get_kaapana_instance(db, node_id, remote=True)

@router.get("/client-kaapana-instance", response_model=schemas.KaapanaInstanceWithJobs)
async def get_client_kaapana_instance(db: Session = Depends(get_db)):
    return crud.get_kaapana_instance(db, remote=False)

@router.post("/get-remote-kaapana-instances", response_model=List[schemas.KaapanaInstance])
async def get_remote_kaapana_instances(filter_kaapana_instances: schemas.FilterKaapanaInstances = None, db: Session = Depends(get_db)):
    if filter_kaapana_instances is None:
        filter_kaapana_instances=schemas.FilterKaapanaInstances(**{'remote': True})
    return crud.get_kaapana_instances(db, filter_kaapana_instances=filter_kaapana_instances)

@router.delete("/kaapana-instance")
async def delete_kaapana_instance(kaapana_instance_id: int, db: Session = Depends(get_db)):
    return crud.delete_kaapana_instance(db, kaapana_instance_id=kaapana_instance_id)

@router.delete("/kaapana-instances")
async def delete_kaapana_instances(db: Session = Depends(get_db)):
    return crud.delete_kaapana_instances(db)

@router.post("/job", response_model=schemas.JobWithKaapanaInstance)
async def create_job(job: schemas.JobCreate, db: Session = Depends(get_db)):
    return crud.create_job(db=db, job=job)

@router.get("/job", response_model=schemas.JobWithKaapanaInstance)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    return crud.get_job(db, job_id)

@router.get("/jobs", response_model=List[schemas.JobWithKaapanaInstance])
async def get_jobs(node_id: str = None, status: str = None, db: Session = Depends(get_db)):
    return crud.get_jobs(db, node_id, status, remote=False)

@router.put("/job", response_model=schemas.JobWithKaapanaInstance)
async def put_job(job: schemas.JobUpdate, db: Session = Depends(get_db)):
    return crud.update_job(db, job, remote=False)

@router.delete("/job")
async def delete_job(job_id: int, db: Session = Depends(get_db)):
    return crud.delete_job(db, job_id, remote=False)

@router.delete("/jobs")
async def delete_jobs(db: Session = Depends(get_db)):
    # Todo add remote job deletion
    return crud.delete_jobs(db)

# @router.get("/dags")
# async def dags(only_dag_names: bool = True):
#     return get_dag_list(only_dag_names=only_dag_names)


# @router.post("/get-instances-dags")
@router.post("/get-dags")
async def ui_form_schemas(filter_kaapana_instances: schemas.FilterKaapanaInstances = None, db: Session = Depends(get_db)):
    if filter_kaapana_instances.remote is False:
        dags = get_dag_list(only_dag_names=True)
        # datasets = get_dataset_list(unique_sets=True)
    else:
        db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=filter_kaapana_instances)
        dags = list(set.intersection(*map(set, [[k for k, v in json.loads(ki.allowed_dags).items()] for ki in db_remote_kaapana_instances ])))
    return JSONResponse(content=dags)

@router.get("/datasets")
async def datasets():
    return get_dataset_list(unique_sets=True)

@router.post("/submit-workflow-schema", response_model=List[schemas.Job])
async def submit_workflow_json_schema(json_schema_data: schemas.JsonSchemaData, db: Session = Depends(get_db)):
    db_client_kaapana = crud.get_kaapana_instance(db, remote=False)
    print(json_schema_data)

    conf_data = {
        **json_schema_data.form_data,
    }

    db_jobs = []
    if json_schema_data.remote == False:
        job = schemas.JobCreate(**{
            "conf_data": conf_data,
            "status": "pending",
            "dag_id": json_schema_data.dag_id,
            "kaapana_instance_id": db_client_kaapana.id
        })
        db_job = crud.create_job(db, job)
        db_jobs.append(db_job)
    else:
        db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=schemas.FilterKaapanaInstances(**{'remote': json_schema_data.remote, 'node_ids': json_schema_data.node_ids}))
        for db_remote_kaapana_instance in db_remote_kaapana_instances:
            job = schemas.JobCreate(**{
                "conf_data": conf_data,
                "status": "queued",
                "dag_id": json_schema_data.dag_id,
                "kaapana_instance_id": db_remote_kaapana_instance.id,
                "addressed_kaapana_node_id": db_client_kaapana.node_id,
            })

            db_job = crud.create_job(db, job)
            db_jobs.append(db_job)

    return db_jobs


@router.get("/check-for-remote-updates", response_model=List[schemas.Job])
async def check_for_remote_updates(db: Session = Depends(get_db)):

    get_remote_updates(db, periodically=False)
    # pending_jobs = []
    # print(100*'#')
    # db_client_kaapana = crud.get_kaapana_instance(db, remote=False)
    # db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=schemas.FilterKaapanaInstances(**{'remote': True}))
    # print('remote kaapana instances', db_remote_kaapana_instances)
    # for db_remote_kaapana_instance in db_remote_kaapana_instances:
    #     same_instance = db_remote_kaapana_instance.node_id == NODE_ID
    #     if same_instance is False:
    #         remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/federated-backend/remote'
    #         print(100*'#')
    #         print(remote_backend_url)

    #     udpate_instance_payload = {
    #         "node_id":  db_client_kaapana.node_id,
    #         "allowed_dags": json.loads(db_client_kaapana.allowed_dags),
    #         "allowed_datasets": json.loads(db_client_kaapana.allowed_datasets)
    #         }

    #     if same_instance is True:
    #         crud.create_and_update_remote_kaapana_instance(
    #             db=db, remote_kaapana_instance=schemas.RemoteKaapanaInstanceUpdateExternal(**udpate_instance_payload), action='external_update')
    #     else:
    #         r = requests.put(f'{remote_backend_url}/remote-kaapana-instance', json=udpate_instance_payload, verify=db_remote_kaapana_instance.ssl_check,
    #         headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
    #         raise_kaapana_connection_error(r)

    #     job_params = {
    #         "node_id": db_client_kaapana.node_id,
    #         "status": "queued"
    #     }
    #     if same_instance is True:
    #         db_incoming_jobs = crud.get_jobs(db, **job_params, remote=True)
    #         incoming_jobs = [schemas.Job(**job.__dict__).dict() for job in db_incoming_jobs]
    #     else:
    #         r = requests.get(f'{remote_backend_url}/jobs', params=job_params, verify=db_remote_kaapana_instance.ssl_check, 
    #         headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
    #         raise_kaapana_connection_error(r)
    #         incoming_jobs =  r.json()
    #     print(len(incoming_jobs))

    #     for incoming_job in incoming_jobs:
    #         incoming_job['kaapana_instance_id'] = db_client_kaapana.id
    #         incoming_job['addressed_kaapana_node_id'] = db_remote_kaapana_instance.node_id
    #         incoming_job['external_job_id'] = incoming_job["id"]
    #         incoming_job['status'] = "pending"
    #         job = schemas.JobCreate(**incoming_job)
    #         db_job = crud.create_job(db, job)
    #         pending_jobs.append(db_job)

    # return pending_jobs

# @router.post("/execute-scheduled-job", response_model=schemas.Job)
# async def execute_scheduled_jobs(job_id: int, db: Session = Depends(get_db)):
#     db_job = crud.get_job(db, job_id)
#     execute_job(db_job)
#     job = schemas.JobUpdate(**{
#         'job_id': db_job.id,
#         'status': 'running',
#         'description':'The worklow was triggered!',
#         'addressed_kaapana_node_id': db_job.addressed_kaapana_node_id,
#         'external_job_id': db_job.external_job_id})

#     crud.update_job(db, job, remote=False)
#     # db_remote_kaapana_instance = crud.get_kaapana_instance(db, node_id=db_job.addressed_kaapana_node_id, remote=True)
#     # remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/federated-backend/remote'
#     # async with httpx.AsyncClient(verify=db_remote_kaapana_instance.ssl_check) as client:
#     #     r = await client.put(f'{remote_backend_url}/job', json={
#     #         "job_id": db_job.external_job_id,
#     #         "status": "running"
#     #     }, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
#     #     raise_kaapana_connection_error(r)
#     #     print(r.json())
#     return db_job


# @router.post("/execute-scheduled-jobs", response_model=List[schemas.Job])
# async def execute_scheduled_jobs(db: Session = Depends(get_db)):
#     executed_scheduled_jobs = []
#     db_client_kaapana = crud.get_kaapana_instance(db, remote=False)
#     for db_job in db_client_kaapana.jobs:
#         if db_job.status == 'scheduled':
#             execute_job(db_job)
#             # Copy of above part
#             job = schemas.JobUpdate(**{
#                 'job_id': db_job.id,
#                 'status': 'running',
#                 'description':'The worklow was triggered!',
#                 'addressed_kaapana_node_id': db_job.addressed_kaapana_node_id,
#                 'external_job_id': db_job.external_job_id})
#             crud.update_job(db, job, remote=False)
#             # db_remote_kaapana_instance = crud.get_kaapana_instance(db, node_id=db_job.addressed_kaapana_node_id, remote=True)
#             # remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/federated-backend/remote'
#             # async with httpx.AsyncClient(verify=db_remote_kaapana_instance.ssl_check) as client:
#             #     r = await client.put(f'{remote_backend_url}/job', json={
#             #         "job_id": db_job.external_job_id,
#             #         "status": "running"
#             #     }, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
#             #     raise_kaapana_connection_error(r)
#             #     print(r.json())
#             # executed_scheduled_jobs.append(db_job)

#     return executed_scheduled_jobs

