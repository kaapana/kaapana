from typing import Optional, List
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, Response, File, Header
from sqlalchemy.orm import Session
from urllib.parse import urlparse
import requests
import httpx
import json
import copy
import asyncio


from app import models
from app.dependencies import get_db
from app import schemas
from app import crud
from app.utils import get_dag_list, get_dataset_list, raise_kaapana_connection_error, execute_job


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

@router.post("/get-remote-kaapana-instances", response_model=List[schemas.KaapanaInstanceWithJobs])
async def get_remote_kaapana_instances(filter_by_node_ids: schemas.FilterByNodeIds = None, db: Session = Depends(get_db)):
    return crud.get_kaapana_instances(db, filter_by_node_ids=filter_by_node_ids)

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

@router.get("/dags")
async def dags(only_dag_names: bool = True):
    return get_dag_list(only_dag_names=only_dag_names)

@router.get("/datasets")
async def datasets():
    return get_dataset_list(unique_sets=True)

@router.get("/workflow-json-schema")
async def workflow_json_schema(remote: bool = False):
    if remote is False:
        dags = get_dag_list(only_dag_names=False)
        datasets = get_dataset_list(unique_sets=True)
        schema = {
            "type": "object",
            "title": "Select a workflow",
            "description": "Depending on which workflow you select, different inputs are required",
            "properties": {
                "dataset": {
                    "type": "string",
                    "title": "Dataset tag",
                    "enum": datasets
                    },
            },
            "oneOf": [],
        }

        for k, v in dags.items():
            if 'ui_forms' in v:
                dag_schema = v['ui_forms']['workflow_form']
                dag_schema['title'] = k
                dag_schema["properties"].update(
                    {
                        "dag": {
                            "type": "string",
                            "const": k
                        }
                    }
                )
                if k == 'nnunet-predict':
                    dag_schema["oneOf"] = []
                    selection_properties = {}
                    base_properties = {}
                    for p_k, p_v in dag_schema['properties'].items():
                        if 'dependsOn' in p_v:
                            p_v.pop('dependsOn')
                            selection_properties[p_k] = p_v
                        else:
                            base_properties[p_k] = p_v
                    base_properties.pop('task')   
                    
                    for task in dag_schema['properties']['task']['enum']:
                        task_selection_properties = copy.deepcopy(selection_properties)
                        for p_k, p_v in task_selection_properties.items():
                            p_v['default'] = v['ui_dag_info'][task][p_k]
                        task_selection_properties.update({
                            "task":
                            {
                                "type": "string",
                                "const": task
                            }
                        })
                        dag_schema["oneOf"].append({
                            "type": 'object',
                            "title": task,
                            "properties": task_selection_properties})
                    dag_schema["properties"] = base_properties
                schema["oneOf"].append(dag_schema)

    return schema

@router.post("/submit-workflow-json-schema", response_model=schemas.Job)
async def submit_workflow_json_schema(workflow_json_schema: schemas.WorkflowJsonSchema, db: Session = Depends(get_db)):
    db_client_kaapana = crud.get_kaapana_instance(db, remote=False)
    print(workflow_json_schema)
    data = workflow_json_schema.data
    print(data)
    dataset = data.pop('dataset')
    dag_id =  data.pop('dag')
    input_modality = data.pop('input', None)
    conf_data = {
        "conf": {
            "form_data": {**data}
        }
    }

    if dataset is not None:
        meta_index_infos = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match_all": {}
                        },
                        {
                            "match_all": {}
                        },
                        {
                            "match_phrase": {
                                "00120020 ClinicalTrialProtocolID_keyword.keyword": {
                                    "query": dataset
                                }
                            }
                        }
                    ],
                    "filter": [],
                    "should": [],
                    "must_not": []
                }
            },
            "index": "meta-index",
            "dag": dag_id,
            "cohort_limit": 2
        }
        # if input_modality is not None:
        #     meta_index_infos["query"]["bool"]["must"].append(
        #         {
        #             "match_phrase": {
        #                 "00080060 Modality_keyword.keyword": {
        #                     "query": input_modality
        #                 }
        #             }
        #         }
        #     )
        conf_data["conf"].update(meta_index_infos)

    job = schemas.JobCreate(**{
        "dry_run": False,
        "conf_data": conf_data,
        "status": "pending",
        "dag_id": "meta-trigger" if dataset is not None else dag_id,
        "kaapana_instance_id": db_client_kaapana.id
    })
    db_job = crud.create_job(db, job)
    return db_job


@router.get("/check-for-remote-updates", response_model=List[schemas.Job])
async def check_for_remote_updates(db: Session = Depends(get_db)):
    pending_jobs = []
    print(100*'#')
    db_client_kaapana = crud.get_kaapana_instance(db, remote=False)
    if db_client_kaapana.automatic_job_execution is True:
        next_status = "scheduled"
        print('scheduled')
    else:
        next_status = "pending"
    db_remote_kaapana_instances = crud.get_kaapana_instances(db, remote=True)
    for db_remote_kaapana_instance in db_remote_kaapana_instances:
        remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/federated-backend/remote'
        print(100*'#')
        print(remote_backend_url)
        async with httpx.AsyncClient(verify=db_remote_kaapana_instance.ssl_check) as client:
            r = await client.put(f'{remote_backend_url}/remote-kaapana-instance', json={
                "node_id":  db_client_kaapana.node_id,
                "allowed_dags": json.loads(db_client_kaapana.allowed_dags),
                "allowed_datasets": json.loads(db_client_kaapana.allowed_datasets)
            }, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
            raise_kaapana_connection_error(r)
        async with httpx.AsyncClient(verify=db_remote_kaapana_instance.ssl_check) as client:
            r = await client.get(f'{remote_backend_url}/jobs', params={
                "node_id": db_client_kaapana.node_id,
                "status": "queued",
            }, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
            raise_kaapana_connection_error(r)
            incoming_jobs =  r.json()
            print(len(incoming_jobs))
            # print(incoming_jobs)
        for incoming_job in incoming_jobs:
            # async with httpx.AsyncClient(verify=db_remote_kaapana_instance.ssl_check) as client:
            #     r = await client.put(f'{remote_backend_url}/job', json={
            #         "job_id": incoming_job['id'],
            #         "status": remote_status
            #     }, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
            #     raise_kaapana_connection_error(r)
            #     # print(r.json())
            incoming_job['kaapana_instance_id'] = db_client_kaapana.id
            incoming_job['addressed_kaapana_node_id'] = db_remote_kaapana_instance.node_id
            incoming_job['external_job_id'] = incoming_job["id"]
            incoming_job['status'] = next_status
            job = schemas.JobCreate(**incoming_job)
            db_job = crud.create_job(db, job)
            # if db_client_kaapana.automatic_job_execution is True:
            #     job = schemas.JobUpdate(**{
            #         'job_id': db_job.id,
            #         'status': 'scheduled',
            #         'description':'The worklow was triggered!'
            #         })
            #     crud.update_job(db, job, remote=False)
            #     print('scheduled')


            pending_jobs.append(db_job)

    return pending_jobs

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

