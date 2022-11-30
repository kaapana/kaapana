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


from app.experiments import models
from app.dependencies import get_db
from app.experiments import schemas
from app.experiments import crud
from app.experiments.utils import get_dag_list, raise_kaapana_connection_error

router = APIRouter(tags=["client"])

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

@router.get("/remote-kaapana-instance", response_model=schemas.KaapanaInstance)
async def get_remote_kaapana_instance(instance_name: str, db: Session = Depends(get_db)):
    return crud.get_kaapana_instance(db, instance_name, remote=True)

@router.get("/client-kaapana-instance", response_model=schemas.KaapanaInstance)
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

@router.post("/job", response_model=schemas.JobWithKaapanaInstance) # changed JobWithKaapanaInstance to JobWithExperiment
async def create_job(request: Request, job: schemas.JobCreate, db: Session = Depends(get_db)):

    if job.username is not None:
        pass
    elif "x-forwarded-preferred-username" in request.headers:
        job.username = request.headers["x-forwarded-preferred-username"]
    else:
        raise HTTPException(status_code=400, detail="A username has to be set when you start a job, either as parameter or in the request!")
    return crud.create_job(db=db, job=job)

@router.get("/job", response_model=schemas.JobWithKaapanaInstance) # changed JobWithKaapanaInstance to JobWithExperiment
async def get_job(job_id: int, db: Session = Depends(get_db)):
    return crud.get_job(db, job_id)

@router.get("/jobs", response_model=List[schemas.JobWithKaapanaInstance])  # changed JobWithKaapanaInstance to JobWithExperiment
async def get_jobs(instance_name: str = None, status: str = None, limit: int = None, db: Session = Depends(get_db)):
    return crud.get_jobs(db, instance_name, status, remote=False, limit=limit)

@router.put("/job", response_model=schemas.JobWithExperiment) # changed JobWithKaapanaInstance to JobWithExperiment
async def put_job(job: schemas.JobUpdate, db: Session = Depends(get_db)):
    # return crud.update_job(db, job, remote=False)
    print(f"We're {job.status}-ing the selected job: {job}")
    if job.status == "abort":
        print(f"We're in put_job() with job.status={job.status}")
        crud.abort_job(db, job, remote=False)
        job.status = "failed"
        return crud.update_job(db, job, remote=False)  # update db_job to failed
    else:
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
    else:
        db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=filter_kaapana_instances)
        dags = list(set.intersection(*map(set, [[k for k, v in json.loads(ki.allowed_dags).items()] for ki in db_remote_kaapana_instances ])))
    return JSONResponse(content=dags)

# @router.post("/submit-workflow-schema", response_model=List[schemas.Job])
# async def submit_workflow_json_schema(request: Request, json_schema_data: schemas.JsonSchemaData, db: Session = Depends(get_db)):
# 
#     username = request.headers["x-forwarded-preferred-username"]
# 
#     db_client_kaapana = crud.get_kaapana_instance(db, remote=False)
#     print(json_schema_data)
# 
#     conf_data = json_schema_data.conf_data
# 
#     conf_data["experiment_form"] = {
#         "username": username
#     }
# 
#     if "data_form" in conf_data and "cohort_name" in conf_data["data_form"]:
#         db_cohort = crud.get_cohort(db, conf_data["data_form"]["cohort_name"])
#         conf_data["data_form"].update({
#             "cohort_query": json.loads(db_cohort.cohort_query),
#             "cohort_identifiers": json.loads(db_cohort.cohort_identifiers)
#         })
#         
#         data_form = conf_data["data_form"]
#         cohort_limit = int(data_form["cohort_limit"]) if ("cohort_limit" in data_form and data_form["cohort_limit"] is not None) else None
#         single_execution = "workflow_form" in conf_data and "single_execution" in conf_data["workflow_form"] and conf_data["workflow_form"]["single_execution"] is True
# 
#         print(f"Single execution: {single_execution}")
#         print(f"Cohort limit: {cohort_limit}")
#     else:
#         single_execution = False
# 
#     queued_jobs = []
#     if single_execution is True:
#         for cohort_identifier in data_form['cohort_identifiers'][:cohort_limit]:
#             # Copying due to reference?!
#             single_conf_data = copy.deepcopy(conf_data)
#             single_conf_data["data_form"]["cohort_identifiers"] = [cohort_identifier]
#             queued_jobs.append({
#                 'conf_data': single_conf_data,
#                 'dag_id': json_schema_data.dag_id,
#                 "username": username
#             })
#     else:
#         queued_jobs = [
#             {
#                 'conf_data': conf_data,
#                 'dag_id': json_schema_data.dag_id,
#                 "username": username
#             }
#         ]
# 
#     db_jobs = []
#     for jobs_to_create in queued_jobs: 
#         if json_schema_data.remote == False:
#             job = schemas.JobCreate(**{
#                 "status": "pending",
#                 "kaapana_instance_id": db_client_kaapana.id,
#                 **jobs_to_create
#             })
#             db_job = crud.create_job(db, job)
#             db_jobs.append(db_job)
#         else:
#             db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=schemas.FilterKaapanaInstances(**{'remote': json_schema_data.remote, 'instance_names': json_schema_data.instance_names}))
#             for db_remote_kaapana_instance in db_remote_kaapana_instances:
#                 job = schemas.JobCreate(**{
#                     "status": "queued",
#                     "kaapana_instance_id": db_remote_kaapana_instance.id,
#                     "addressed_kaapana_instance_name": db_client_kaapana.instance_name,
#                     **jobs_to_create
#                 })
# 
#                 db_job = crud.create_job(db, job)
#                 db_jobs.append(db_job)
# 
#     return db_jobs

@router.post("/get-ui-form-schemas")
async def ui_form_schemas(request: Request, filter_kaapana_instances: schemas.FilterKaapanaInstances = None, db: Session = Depends(get_db)):

    username = request.headers["x-forwarded-preferred-username"]
    dag_id = filter_kaapana_instances.dag_id
    schemas = {}
    if dag_id is None:
        return JSONResponse(content=schemas)

    # Checking for dags
    if filter_kaapana_instances.remote is False:
        dags = get_dag_list(only_dag_names=False)
        # datasets = crud.get_cohorts(unique_sets=True, username=username)
    else:
        db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=filter_kaapana_instances)
        # datasets = set.intersection(*map(set,[json.loads(ki.allowed_datasets) for ki in db_remote_kaapana_instances]))
        in_common_dags_set = set.intersection(*map(set, [[k for k, v in json.loads(ki.allowed_dags).items()] for ki in db_remote_kaapana_instances ]))
        dags = {}
        for el in in_common_dags_set:
            dags.update({el: json.loads(db_remote_kaapana_instances[0].allowed_dags)[el]})

    if dag_id not in dags:
        raise HTTPException(status_code=404, detail=f"Dag {dag_id} is not part of the allowed dags, please add it!")
    dag = dags[dag_id]
    schemas = dag["ui_forms"]
    print(schemas)
    # Checking for cohorts...
    if "data_form" in schemas and "properties" in schemas["data_form"] and  "cohort_name" in schemas["data_form"]["properties"]:
        if filter_kaapana_instances.remote is False:
            datasets = crud.get_cohorts(db, username=username)
        else:
            db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=filter_kaapana_instances)
            datasets = set.intersection(*map(set,[json.loads(ki.allowed_datasets) for ki in db_remote_kaapana_instances]))
        print(datasets)
        schemas["data_form"]["properties"]["cohort_name"]["oneOf"] = [{"const": d, "title": d} for d in datasets]

    # if 'ui_forms' in dag:
    #     for ui_form_key, ui_form in dag['ui_forms'].items():
    #         ui_dag_info = dag['ui_dag_info'] if 'ui_dag_info' in dag else None
    #         #schema_data[ui_form_key] = get_schema(dag_id, ui_form_key, ui_form, ui_dag_info, filter_kaapana_instances, db)
    return JSONResponse(content=schemas)

@router.get("/check-for-remote-updates")
async def check_for_remote_updates(db: Session = Depends(get_db)):
    crud.get_remote_updates(db, periodically=False)
    return {f"Federated backend is up and running!"}

@router.post("/cohort", response_model=schemas.Cohort)
async def create_cohort(request: Request, cohort: schemas.CohortCreate, db: Session = Depends(get_db)):
    cohort.username = request.headers["x-forwarded-preferred-username"]
    return crud.create_cohort(db=db, cohort=cohort)

@router.get("/cohort", response_model=schemas.Cohort)
async def get_cohort(cohort_name: str, db: Session = Depends(get_db)):
    return crud.get_cohort(db, cohort_name)

@router.get("/cohorts", response_model=List[schemas.Cohort])
async def get_cohorts(request: Request, instance_name: str = None, limit: int = None, db: Session = Depends(get_db)):
    return crud.get_cohorts(db, instance_name, limit=limit, as_list=False, username=request.headers["x-forwarded-preferred-username"])

@router.get("/cohort-names")
async def get_cohort_names(request: Request, db: Session = Depends(get_db)):
    return crud.get_cohorts(db, username=request.headers["x-forwarded-preferred-username"])

@router.put("/cohort", response_model=schemas.Cohort)
async def put_cohort(cohort: schemas.CohortUpdate, db: Session = Depends(get_db)):
    return crud.update_cohort(db, cohort)

@router.delete("/cohort")
async def delete_cohort(cohort_name: str, db: Session = Depends(get_db)):
    return crud.delete_cohort(db, cohort_name)

@router.delete("/cohorts")
async def delete_cohorts(db: Session = Depends(get_db)):
    return crud.delete_cohorts(db)

# create_experiment ; should replace and be sth like "def submit_workflow_json_schema()"
@router.post("/experiment", response_model=schemas.Experiment)   # schemas.ExperimentWithKaapanaInstance
async def create_experiment(request: Request, json_schema_data: schemas.JsonSchemaData, db: Session = Depends(get_db)):
    print(f"Here comes the one and only json_schema_data: {json_schema_data}")
    print(f"Experiment Name: {json_schema_data.experiment_name}")
    
    if json_schema_data.username is not None:
        username = json_schema_data.username
    elif "x-forwarded-preferred-username" in request.headers:
        username = request.headers["x-forwarded-preferred-username"]
    else:
        raise HTTPException(status_code=400, detail="A username has to be set when you submit a workflow schema, either as parameter or in the request!")


    db_client_kaapana = crud.get_kaapana_instance(db, remote=False)
    print(json_schema_data)

    conf_data = json_schema_data.conf_data
    print(f"Here comes the one and only conf_data: {conf_data}")

    conf_data["experiment_form"] = {
        "username": username
    }

    if "data_form" in conf_data and "cohort_name" in conf_data["data_form"]:
        db_cohort = crud.get_cohort(db, conf_data["data_form"]["cohort_name"])
        conf_data["data_form"].update({
            "cohort_query": json.loads(db_cohort.cohort_query),
            "cohort_identifiers": [identifier.identifier for identifier in db_cohort.cohort_identifiers]
        })
        
        data_form = conf_data["data_form"]
        cohort_limit = int(data_form["cohort_limit"]) if ("cohort_limit" in data_form and data_form["cohort_limit"] is not None) else None
        single_execution = "workflow_form" in conf_data and "single_execution" in conf_data["workflow_form"] and conf_data["workflow_form"]["single_execution"] is True

        print(f"Single execution: {single_execution}")
        print(f"Cohort limit: {cohort_limit}")
    else:
        single_execution = False

    queued_jobs = []
    if single_execution is True:
        for cohort_identifier in data_form['cohort_identifiers'][:cohort_limit]:
            # Copying due to reference?!
            single_conf_data = copy.deepcopy(conf_data)
            single_conf_data["data_form"]["cohort_identifiers"] = [cohort_identifier]
            queued_jobs.append({
                'conf_data': single_conf_data,
                'dag_id': json_schema_data.dag_id,
                "username": username
            })
    else:
        queued_jobs = [
            {
                'conf_data': conf_data,
                'dag_id': json_schema_data.dag_id,
                "username": username
            }
        ]
    print(f"Queued jobs: {queued_jobs}")    # still works
    
    db_jobs = []
    db_kaapana_instances = []
    for jobs_to_create in queued_jobs: 
        if json_schema_data.remote == False:
            job = schemas.JobCreate(**{
                "status": "pending",
                "kaapana_instance_id": db_client_kaapana.id,
                **jobs_to_create
            })
            print("schemas.JobCreate was successful!")   # still works
            db_job = crud.create_job(db, job)
            print("crud.create_job() was successful!")
            db_jobs.append(db_job)
            db_kaapana_instances.append(db_client_kaapana)
        else:
            db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=schemas.FilterKaapanaInstances(**{'remote': json_schema_data.remote, 'instance_names': json_schema_data.instance_names}))
            for db_remote_kaapana_instance in db_remote_kaapana_instances:
                job = schemas.JobCreate(**{
                    "status": "queued",
                    "kaapana_instance_id": db_remote_kaapana_instance.id,
                    "addressed_kaapana_instance_name": db_client_kaapana.instance_name,
                    **jobs_to_create
                })

                db_job = crud.create_job(db, job)
                db_jobs.append(db_job)
                db_kaapana_instances.append(db_remote_kaapana_instance)
    print(f"Jobs successfully created: {db_jobs}")  # still works

    print(f"db_cohort.cohort_name: {db_cohort.cohort_name}")
    # create an experiment and add jobs to it
    experiment = schemas.ExperimentCreate(**{
        "experiment_name": json_schema_data.experiment_name,
        "username": username,
        "kaapana_instance_id": db_client_kaapana.id,
        "experiment_jobs": db_jobs,
        # "involved_kaapana_instances": db_remote_kaapana_instance,
        "cohort_name": db_cohort.cohort_name,
    })
    print("schemas.ExperimentCreate was successful")
    db_experiment = crud.create_experiment(db=db, experiment=experiment)
    print("crud.create_experiment() was successful")

    return db_experiment

# get_experiment
@router.get("/experiment", response_model=schemas.ExperimentWithKaapanaInstance)
async def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    return crud.get_experiment(db, experiment_id)

# get_experiments
@router.get("/experiments", response_model=List[schemas.ExperimentWithKaapanaInstance])
async def get_experiments(request: Request, instance_name: str = None, limit: int = None, db: Session = Depends(get_db)):
    return crud.get_experiments(db, instance_name, limit=limit) # , username=request.headers["x-forwarded-preferred-username"]

@router.get("/experiment_jobs", response_model=List[schemas.JobWithExperiment])  # changed JobWithKaapanaInstance to JobWithExperiment
async def get_experiment_jobs(experiment_name: str = None, status: str = None, limit: int = None, db: Session = Depends(get_db)):
    return crud.get_experiment_jobs(db, experiment_name, status, limit=limit)

# put/update_experiment
@router.put("/experiment", response_model=schemas.Experiment)
async def put_experiment(experiment: schemas.ExperimentUpdate, db: Session = Depends(get_db)):
    print(f"Experiment Status in put_experiment: {experiment.experiment_status}")
    if experiment.experiment_status == "abort":
        # iterate over experiment's jobs and execute crud.abort_job() and crud.update_job() and at the end also crud.update_experiment()
        db_experiment = await get_experiment(experiment.experiment_id, db)
        print(f"experiment: {experiment} ; db_experiment: {db_experiment}")
        for db_job in db_experiment.experiment_jobs:
            print(f"To-be-aborted Job: {db_job} with id: {db_job.id}")
            
            # compose a JobUpdate schema, set it's status to 'abort' and execute client.py's put_job()
            job = schemas.JobUpdate(**{
                'job_id': db_job.id,
                'status': 'abort',
                'description':'The job was aborted by the user!'
                })
            print(f"Job JobUpdate object: {job}")

            # put_job(job, db)  # would be easier but doesb't work, so let's do it manually
            crud.abort_job(db, job, remote=False)
            job.status = "failed"
            crud.update_job(db, job, remote=False)  # update db_job to failed
            
        # update aborted experiment
        return crud.update_experiment(db, experiment)

        # print(f"We're in put_job() with job.status={job.status}")
        # crud.abort_job(db, job, remote=False)
        # job.status = "failed"
        # return crud.update_job(db, job, remote=False)  # update db_job to failed
        pass
    else:
        return crud.update_experiment(db, experiment)

# delete_experiment
@router.delete("/experiment")
async def delete_experiment(experiment_id: int, db: Session = Depends(get_db)):
    return crud.delete_experiment(db, experiment_id)

# delete_experiments
@router.delete("/experiments")
async def delete_experiments(db: Session = Depends(get_db)):
    return crud.delete_experiments(db)


@router.post("/identifier", response_model=schemas.Identifier)
async def create_identifier(identifier: schemas.Identifier, db: Session= Depends(get_db)):
    resp = crud.create_identifier(db=db, identifier=identifier)
    print('response', resp)
    return resp

@router.delete("/identifier")
async def delete_cohort(identifier: str, db: Session = Depends(get_db)):
    return crud.delete_identifier(db, identifier)

@router.get("/identifiers", response_model=List[schemas.Identifier])
async def get_identifiers(db: Session = Depends(get_db)):
    return crud.get_identifiers(db)

@router.delete("/identifiers")
async def get_identifiers(db: Session = Depends(get_db)):
    return crud.delete_identifiers(db)
