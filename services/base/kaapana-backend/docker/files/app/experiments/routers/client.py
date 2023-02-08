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
    print(f"filter_kaapana_instances: {filter_kaapana_instances}")
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

@router.get("/get_job_taskinstances")
async def get_job_taskinstances(job_id: int, db: Session = Depends(get_db)):
    print("We made it to client.py's def get_job_taskinstances()!")
    return crud.get_job_taskinstances(db, job_id)

# @router.get("/dags")
# async def dags(only_dag_names: bool = True):
#     return get_dag_list(only_dag_names=only_dag_names)


# @router.post("/get-instances-dags")
@router.post("/get-dags")
async def ui_form_schemas(filter_kaapana_instances: schemas.FilterKaapanaInstances = None, db: Session = Depends(get_db)):
    print(f"GET DAGS filter_kaapana_instances.instance_names: {filter_kaapana_instances.instance_names}")

    if len(filter_kaapana_instances.instance_names)==0 and filter_kaapana_instances.remote is False:    # necessary from old implementation to get dags in client instance view
        dags = get_dag_list(only_dag_names=True)
        return JSONResponse(content=dags)

    db_client_kaapana = crud.get_kaapana_instance(db, remote=False)    # get client_instance
    dags = {}
    for instance_name in filter_kaapana_instances.instance_names:
        # check if whether instance_name is client_instance --> dags = get_dag_list(only_dag_names=True)
        if db_client_kaapana.instance_name == instance_name:
            client_dags = get_dag_list(only_dag_names=True)    # or rather get allowed_dags of db_client_kaapana, but also a little bit unnecessary to restrict local dags
            # print(f"client_dags: {client_dags}")
            dags[db_client_kaapana.instance_name] = client_dags
        else:
            db_remote_kaapana_instance = crud.get_kaapana_instance(db, instance_name, remote=True)
            if db_remote_kaapana_instance:
                # print(f"db_remote_kaapana_instance: {db_remote_kaapana_instance}")
                remote_allowed_dags = list(json.loads(db_remote_kaapana_instance.allowed_dags).keys())
                dags[db_remote_kaapana_instance.instance_name] = remote_allowed_dags
    # print(f"Dags: {dags}")
    if len(dags) > 1:   # if multiple instances are selected -> find intersection of their allowed dags
        overall_allowed_dags = []
        for i in range(len(dags)-1):
            if len(overall_allowed_dags) == 0:
                list1 = list(dags.values())[i]
                list2 = list(dags.values())[i+1]
                overall_allowed_dags = list(set(list1) & set(list2))
            else:
                list1 = list(dags.values())[i]
                overall_allowed_dags = list(set(overall_allowed_dags) & set(list1))
        print(f"Overall_allowed_dags: {overall_allowed_dags}")
        return JSONResponse(content=overall_allowed_dags)
    elif len(dags) == 1:    # if just one instance is selected -> return (allowed) dags of this instance
        return JSONResponse(content=list(dags.values())[0])

    # old code of function def ui_form_schemas(...)
    # if filter_kaapana_instances.remote is False:
    #     dags = get_dag_list(only_dag_names=True)
    # else:
    #     db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=filter_kaapana_instances)
    #     dags = list(set.intersection(*map(set, [[k for k, v in json.loads(ki.allowed_dags).items()] for ki in db_remote_kaapana_instances ])))
    # return JSONResponse(content=dags)

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
    
    # DAGs: Checking for dags -> replace with new implementation!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    db_client_kaapana = crud.get_kaapana_instance(db, remote=False)    # get client_instance
    dags = {}
    just_all_dags = {}
    for instance_name in filter_kaapana_instances.instance_names:
        # check if whether instance_name is client_instance --> dags = get_dag_list(only_dag_names=True)
        if db_client_kaapana.instance_name == instance_name:
            client_dags = get_dag_list(only_dag_names=False)    # get dags incl. its meta information (not only dag_name)
            # print(f"client_dags: {client_dags}\n\n client_dags.values(): {client_dags.values()}")
            dags[db_client_kaapana.instance_name] = client_dags
            just_all_dags = {**just_all_dags, **client_dags}
            # not all runner instances are remote instances --> set remote to False
            schemas["remote"] = False
        else:
            db_remote_kaapana_instance = crud.get_kaapana_instance(db, instance_name, remote=True)
            remote_allowed_dags = json.loads(db_remote_kaapana_instance.allowed_dags)   # w/o .keys() --> get dags incl. its meta information (not only dag_name)
            # print(f"remote_allowed_dags: {remote_allowed_dags}\n\n remote_allowed_dags.values(): {remote_allowed_dags.values()}")
            dags[db_remote_kaapana_instance.instance_name] = remote_allowed_dags
            just_all_dags = {**just_all_dags, **remote_allowed_dags}
    if len(dags) > 1:   # if multiple instances are selected -> find intersection of their allowed dags
        overall_allowed_dags = []
        for i in range(len(dags)-1):
            if len(overall_allowed_dags) == 0:
                list1 = list(dags.values())[i]
                # print(f"list1: {list1}")
                list2 = list(dags.values())[i+1]
                overall_allowed_dags = list(set(list1) & set(list2))
            else:
                list1 = list(dags.values())[i]
                overall_allowed_dags = list(set(overall_allowed_dags) & set(list1))
        # get details of overall_allowed_dags
        overall_allowed_dags_datailed = {}
        for overall_allowed_dag in overall_allowed_dags:
            overall_allowed_dags_datailed[overall_allowed_dag] = just_all_dags[overall_allowed_dag]
        dags = overall_allowed_dags_datailed
    elif len(dags) == 1:    # if just one instance is selected -> return (allowed) dags of this instance
        dags = list(dags.values())[0]

    if dag_id not in dags:
        raise HTTPException(status_code=404, detail=f"Dag {dag_id} is not part of the allowed dags, please add it!")
    dag = dags[dag_id]
    # print(f"dags: {dags}")
    schemas = dag["ui_forms"]
    # print(f"schemas: {schemas}")

    # Cohorts: Checking for cohorts
    if "data_form" in schemas and "properties" in schemas["data_form"] and  "cohort_name" in schemas["data_form"]["properties"]:
        db_client_kaapana = crud.get_kaapana_instance(db, remote=False)    # get client_instance
        datasets = {}
        for instance_name in filter_kaapana_instances.instance_names:
            # check if whether instance_name is client_instance --> datasets = crud.get_cohorts(db, username=username)
            if db_client_kaapana.instance_name == instance_name:
                client_datasets = crud.get_cohorts(db, username=username)    # or rather get allowed_datasets of db_client_kaapana, but also a little bit unnecessary to restrict local datasets
                # print(f"client_datasets: {client_datasets}")
                datasets[db_client_kaapana.instance_name] = client_datasets
            else:
                db_remote_kaapana_instance = crud.get_kaapana_instance(db, instance_name, remote=True)
                # print(f"db_remote_kaapana_instance: {db_remote_kaapana_instance}")
                remote_allowed_datasets = list(json.loads(db_remote_kaapana_instance.allowed_datasets))
                datasets[db_remote_kaapana_instance.instance_name] = remote_allowed_datasets
        # print(f"datasets: {datasets}")
        if len(datasets) > 1:   # if multiple instances are selected -> find intersection of their allowed datasets
            overall_allowed_datasets = []
            for i in range(len(datasets)-1):
                if len(overall_allowed_datasets) == 0:
                    list1 = list(datasets.values())[i]
                    list2 = list(datasets.values())[i+1]
                    overall_allowed_datasets = list(set(list1) & set(list2))
                else:
                    list1 = list(datasets.values())[i]
                    overall_allowed_datasets = list(set(overall_allowed_datasets) & set(list1))
            print(f"Overall_allowed_datasets: {overall_allowed_datasets}")
            schemas["data_form"]["properties"]["cohort_name"]["oneOf"] = [{"const": d, "title": d} for d in overall_allowed_datasets]
        elif len(datasets) == 1:    # if just one instance is selected -> return (allowed) datasets of this instance
            schemas["data_form"]["properties"]["cohort_name"]["oneOf"] = [{"const": d, "title": d} for d in list(datasets.values())[0]]

        # old cohort code
        # if filter_kaapana_instances.remote is False:
        #     datasets = crud.get_cohorts(db, username=username)
        # else:
        #     db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=filter_kaapana_instances)
        #     datasets = set.intersection(*map(set,[json.loads(ki.allowed_datasets) for ki in db_remote_kaapana_instances]))
        # print(datasets)
        # schemas["data_form"]["properties"]["cohort_name"]["oneOf"] = [{"const": d, "title": d} for d in datasets]
    
    print(f"\n\nFinal Schema: \n{schemas}")
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
    print(f"CREATE EXPERIMENT {json_schema_data.experiment_name} with json_schema_data: {json_schema_data}")
    
    if json_schema_data.username is not None:
        username = json_schema_data.username
    elif "x-forwarded-preferred-username" in request.headers:
        username = request.headers["x-forwarded-preferred-username"]
    else:
        raise HTTPException(status_code=400, detail="A username has to be set when you submit a workflow schema, either as parameter or in the request!")


    db_client_kaapana = crud.get_kaapana_instance(db, remote=False)
    # if db_client_kaapana.instance_name in json_schema_data.instance_names:  # check or correct: if client_kaapana_instance in experiment's runner instances ...
    #     json_schema_data.remote = False                                     # ... set json_schema_data.remote to False

    conf_data = json_schema_data.conf_data
    # print(f"Here comes the one and only conf_data: {conf_data}")

    print(f"json_schema_data.instance_names: {json_schema_data.instance_names}")
    if json_schema_data.federated:  # == True ;-)
        involved_instance_names = copy.deepcopy(json_schema_data.instance_names)
        involved_instance_names.extend(conf_data['external_schema_instance_names'])
    print(f"json_schema_data.instance_names: {json_schema_data.instance_names}")
    conf_data["experiment_form"] = {
        "username": username,
        "experiment_name": json_schema_data.experiment_name,
        "involved_instances": json_schema_data.instance_names if json_schema_data.federated == False else involved_instance_names, # instances on which experiment is created!
        "runner_instances": json_schema_data.instance_names    # instances on which jobs of experiment are created!
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
        db_cohort = None

    print(f"Conf data: {conf_data}")
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
                # 'dag_id': json_schema_data.dag_id if json_schema_data.federated == False else conf_data['external_schema_federated_form']['remote_dag_id'],
                "username": username
            }
        ]

    print(f"Queued jobs: {queued_jobs}")
    
    # create jobs on conf_data["experiment_form"]["runner_instances"]
    db_jobs = []
    db_kaapana_instances = []
    kaapana_instances_names = []
    for jobs_to_create in queued_jobs: 
        print(f"jobs_to_create: {jobs_to_create}")

        # db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=schemas.FilterKaapanaInstances(**{'remote': json_schema_data.remote, 
        #         'instance_names': json_schema_data.instance_names
        #         }))
        db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=schemas.FilterKaapanaInstances(**{'remote': json_schema_data.remote, 
                'instance_names': conf_data["experiment_form"]["runner_instances"]
                }))
        # if db_client_kaapana.instance_name in conf_data['experiment_form']['involved_instances']:  # add client instance to instance list only if it is marked as an involved_instance of current experiment
        #     db_kaapana_instances.append(db_client_kaapana)
        if db_client_kaapana.instance_name in conf_data['experiment_form']['runner_instances']:  # add client instance to instance list only if it is marked as an involved_instance of current experiment
            db_kaapana_instances.append(db_client_kaapana)
        db_kaapana_instances.extend(db_remote_kaapana_instances)
        db_kaapana_instances_set = set(db_kaapana_instances)
        print(f"Experiment-executing Instances: {db_kaapana_instances_set} from db_kaapana_instances: {db_kaapana_instances}")

        for db_kaapana_instance in db_kaapana_instances_set:
            print(f"db_kaapana_instance.id: {db_kaapana_instance.id} ; db_client_kaapana.instance_name: {db_client_kaapana.instance_name}")
            job = schemas.JobCreate(**{
                "status": "queued",
                "kaapana_instance_id": db_kaapana_instance.id,
                "owner_kaapana_instance_name": db_client_kaapana.instance_name,
                **jobs_to_create
            })
            print(f"JobCreate in client: {job}")

            db_job = crud.create_job(db, job)
            db_jobs.append(db_job)
            kaapana_instances_names.append(str(json.dumps(db_kaapana_instance.instance_name)))
    print(f"Jobs successfully created: {db_jobs}")

    # create an experiment with involved_instances=conf_data["experiment_form"]["involved_instances"] and add jobs to it
    print(f"kaapana_instances_names: {kaapana_instances_names}; type-of: {type(kaapana_instances_names)}")
    kaapana_instances_names = [db_kaapana_instance.instance_name for db_kaapana_instance in db_kaapana_instances_set]
    print(f"kaapana_instances_names: {kaapana_instances_names}; type-of: {type(kaapana_instances_names)}")
    experiment = schemas.ExperimentCreate(**{
        "experiment_name": json_schema_data.experiment_name,
        "username": username,
        "kaapana_instance_id": db_client_kaapana.id,
        "experiment_jobs": db_jobs,
        # "involved_kaapana_instances": kaapana_instances_names,
        "involved_kaapana_instances": conf_data["experiment_form"]["involved_instances"],
        "cohort_name": db_cohort.cohort_name if db_cohort is not None else None,
    })
    print(f"schemas.ExperimentCreate was successful: {experiment}")
    db_experiment = crud.create_experiment(db=db, experiment=experiment)
    print("crud.create_experiment() was successful")
    print(f"Experiment's involved instances: {db_experiment.involved_kaapana_instances}")

    return db_experiment

# get_experiment
@router.get("/experiment", response_model=schemas.ExperimentWithKaapanaInstance) # response_model=schemas.ExperimentWithKaapanaInstance
async def get_experiment(experiment_id: int = None, experiment_name: str = None, db: Session = Depends(get_db)):
    return crud.get_experiment(db, experiment_id, experiment_name)

# get_experiments
@router.get("/experiments", response_model=List[schemas.ExperimentWithKaapanaInstance]) # also okay: response_model=List[schemas.Experiment]
async def get_experiments(request: Request, instance_name: str = None, involved_instance_name: str = None, experiment_job_id: int = None, limit: int = None, db: Session = Depends(get_db)):
    return crud.get_experiments(db, instance_name, involved_instance_name, experiment_job_id, limit=limit) # , username=request.headers["x-forwarded-preferred-username"]

@router.get("/experiment_jobs", response_model=List[schemas.JobWithKaapanaInstance])  # changed JobWithKaapanaInstance to JobWithExperiment
async def get_experiment_jobs(experiment_name: str = None, status: str = None, limit: int = None, db: Session = Depends(get_db)):
    exp_jobs = crud.get_experiment_jobs(db, experiment_name, status, limit=limit)
    # print(f"in get_experiment_jobs(): {exp_jobs}")
    return exp_jobs
    # return crud.get_experiment_jobs(db, experiment_name, status, limit=limit)

# put/update_experiment
@router.put("/experiment", response_model=schemas.Experiment)
async def put_experiment(experiment: schemas.ExperimentUpdate, db: Session = Depends(get_db)):
    print(f"Experiment Status in put_experiment: {experiment.experiment_status}")
    if experiment.experiment_status == "abort":
        # iterate over experiment's jobs and execute crud.abort_job() and crud.update_job() and at the end also crud.update_experiment()
        db_experiment = crud.get_experiment(db, experiment.experiment_id)   # better call crud method directly instead of calling client.py's def get_experiment()
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
    else:
        return crud.update_experiment(db, experiment)

# endpoint to update an experiment with additional experiment_jobs
@router.put("/experiment_jobs", response_model=schemas.Experiment)
async def put_experiment_jobs(experiment: schemas.ExperimentUpdate, db: Session = Depends(get_db)):
    return crud.put_experiment_jobs(db, experiment)

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
