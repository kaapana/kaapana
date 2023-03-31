import copy
import json
import logging
from typing import List, Union

import jsonschema
from app.datasets.utils import execute_opensearch_query
from app.dependencies import get_db
from app.experiments import crud
from app.experiments import schemas
from app.experiments.utils import HelperMinio
from app.experiments.utils import get_dag_list
from fastapi import APIRouter, Depends, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from pydantic.schema import schema
from sqlalchemy.orm import Session

logging.getLogger().setLevel(logging.DEBUG)

router = APIRouter(tags=["client"])

@router.post("/post-minio-object-to-uploads")
async def post_minio_object_to_uploads(filepond: UploadFile = File(...)):
    logging.info('Uploading file:', filepond.filename)
    HelperMinio.minioClient.put_object("uploads", filepond.filename, filepond.file, length=-1, part_size=10*1024*1024)
    return JSONResponse(content={"message": "Succesfully uploaded file " + filepond.filename})

@router.post("/remote-kaapana-instance", response_model=schemas.KaapanaInstance)
def create_remote_kaapana_instance(remote_kaapana_instance: schemas.RemoteKaapanaInstanceCreate, db: Session = Depends(get_db)):
    return crud.create_and_update_remote_kaapana_instance(db=db, remote_kaapana_instance=remote_kaapana_instance)

@router.post("/client-kaapana-instance", response_model=schemas.KaapanaInstance)
def create_client_kaapana_instance(client_kaapana_instance: schemas.ClientKaapanaInstanceCreate, db: Session = Depends(get_db)):
    return crud.create_and_update_client_kaapana_instance(db=db, client_kaapana_instance=client_kaapana_instance)

@router.put("/remote-kaapana-instance", response_model=schemas.KaapanaInstance)
def put_remote_kaapana_instance(remote_kaapana_instance: schemas.RemoteKaapanaInstanceCreate, db: Session = Depends(get_db)):
    return crud.create_and_update_remote_kaapana_instance(db=db, remote_kaapana_instance=remote_kaapana_instance, action='update')

@router.put("/client-kaapana-instance", response_model=schemas.KaapanaInstance)
def put_client_kaapana_instance(client_kaapana_instance: schemas.ClientKaapanaInstanceCreate, db: Session = Depends(get_db)):
    return crud.create_and_update_client_kaapana_instance(db=db, client_kaapana_instance=client_kaapana_instance, action='update')

@router.get("/remote-kaapana-instance", response_model=schemas.KaapanaInstance)
def get_remote_kaapana_instance(instance_name: str, db: Session = Depends(get_db)):
    return crud.get_kaapana_instance(db, instance_name, remote=True)


@router.get("/client-kaapana-instance", response_model=schemas.KaapanaInstance)
def get_client_kaapana_instance(db: Session = Depends(get_db)):
    return crud.get_kaapana_instance(db, remote=False)

@router.post("/get-remote-kaapana-instances", response_model=List[schemas.KaapanaInstance])
def get_remote_kaapana_instances(filter_kaapana_instances: schemas.FilterKaapanaInstances = None, db: Session = Depends(get_db)):
    if filter_kaapana_instances is None:
        filter_kaapana_instances = schemas.FilterKaapanaInstances(**{"remote": True})
    return crud.get_kaapana_instances(
        db, filter_kaapana_instances=filter_kaapana_instances
    )


@router.delete("/kaapana-instance")
def delete_kaapana_instance(kaapana_instance_id: int, db: Session = Depends(get_db)):
    return crud.delete_kaapana_instance(db, kaapana_instance_id=kaapana_instance_id)


@router.delete("/kaapana-instances")
def delete_kaapana_instances(db: Session = Depends(get_db)):
    return crud.delete_kaapana_instances(db)

@router.post("/job", response_model=schemas.JobWithKaapanaInstance) # also okay: JobWithExperiment
def create_job(request: Request, job: schemas.JobCreate, db: Session = Depends(get_db)):
    if job.username is not None:
        pass
    elif "x-forwarded-preferred-username" in request.headers:
        job.username = request.headers["x-forwarded-preferred-username"]
    else:
        raise HTTPException(
            status_code=400,
            detail="A username has to be set when you start a job, either as parameter or in the request!",
        )
    return crud.create_job(db=db, job=job)

@router.get("/job", response_model=schemas.JobWithKaapanaInstance) # also okay: JobWithExperiment
def get_job(job_id: int = None, run_id: str = None, db: Session = Depends(get_db)):
    return crud.get_job(db, job_id, run_id)

@router.get("/jobs", response_model=List[schemas.JobWithExperimentWithKaapanaInstance])  # also okay: JobWithExperiment; JobWithKaapanaInstance
def get_jobs(instance_name: str = None, experiment_name: str = None, status: str = None, limit: int = None, db: Session = Depends(get_db)):
    return crud.get_jobs(db, instance_name, experiment_name, status, remote=False, limit=limit)

@router.put("/job", response_model=schemas.JobWithExperiment) # changed JobWithKaapanaInstance to JobWithExperiment
def put_job(job: schemas.JobUpdate, db: Session = Depends(get_db)):
    # return crud.update_job(db, job, remote=False)
    if job.status == "abort":
        crud.abort_job(db, job, remote=False)
        job.status = "failed"
        return crud.update_job(db, job, remote=False)  # update db_job to failed
    else:
        return crud.update_job(db, job, remote=False)


@router.delete("/job")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    return crud.delete_job(db, job_id, remote=False)


@router.delete("/jobs")
def delete_jobs(db: Session = Depends(get_db)):
    # Todo add remote job deletion
    return crud.delete_jobs(db)


@router.get("/dags")
async def dags(only_dag_names: bool = True):
    return get_dag_list(only_dag_names=only_dag_names)


@router.get("/get_job_taskinstances")
def get_job_taskinstances(job_id: int, db: Session = Depends(get_db)):
    return crud.get_job_taskinstances(db, job_id)


@router.post("/get-dags")
def ui_form_schemas(filter_kaapana_instances: schemas.FilterKaapanaInstances = None, db: Session = Depends(get_db)):

    if len(filter_kaapana_instances.instance_names)==0 and filter_kaapana_instances.remote is False:    # necessary from old implementation to get dags in client instance view
        dags = get_dag_list(only_dag_names=True)
        return JSONResponse(content=dags)

    db_client_kaapana = crud.get_kaapana_instance(
        db, remote=False
    )  # get client_instance
    dags = {}
    for instance_name in filter_kaapana_instances.instance_names:
        # check if whether instance_name is client_instance --> dags = get_dag_list(only_dag_names=True)
        if db_client_kaapana.instance_name == instance_name:
            client_dags = get_dag_list(
                only_dag_names=True
            )  # or rather get allowed_dags of db_client_kaapana, but also a little bit unnecessary to restrict local dags
            dags[db_client_kaapana.instance_name] = client_dags
        else:
            db_remote_kaapana_instance = crud.get_kaapana_instance(
                db, instance_name, remote=True
            )
            if db_remote_kaapana_instance:
                remote_allowed_dags = list(
                    json.loads(db_remote_kaapana_instance.allowed_dags).keys()
                )
                dags[db_remote_kaapana_instance.instance_name] = remote_allowed_dags
    if (
        len(dags) > 1
    ):  # if multiple instances are selected -> find intersection of their allowed dags
        overall_allowed_dags = []
        for i in range(len(dags) - 1):
            if len(overall_allowed_dags) == 0:
                list1 = list(dags.values())[i]
                list2 = list(dags.values())[i + 1]
                overall_allowed_dags = list(set(list1) & set(list2))
            else:
                list1 = list(dags.values())[i]
                overall_allowed_dags = list(set(overall_allowed_dags) & set(list1))
        return JSONResponse(content=overall_allowed_dags)
    elif (
        len(dags) == 1
    ):  # if just one instance is selected -> return (allowed) dags of this instance
        return JSONResponse(content=list(dags.values())[0])


@router.post("/get-ui-form-schemas")
def ui_form_schemas(request: Request, filter_kaapana_instances: schemas.FilterKaapanaInstances = None, db: Session = Depends(get_db)):

    username = request.headers["x-forwarded-preferred-username"]
    dag_id = filter_kaapana_instances.dag_id
    schemas = {}
    if dag_id is None:
        return JSONResponse(content=schemas)

    # DAGs: Checking for dags -> replace with new implementation!
    db_client_kaapana = crud.get_kaapana_instance(
        db, remote=False
    )  # get client_instance
    dags = {}
    just_all_dags = {}
    for instance_name in filter_kaapana_instances.instance_names:
        # check if whether instance_name is client_instance --> dags = get_dag_list(only_dag_names=True)
        if db_client_kaapana.instance_name == instance_name:
            client_dags = get_dag_list(
                only_dag_names=False
            )  # get dags incl. its meta information (not only dag_name)
            dags[db_client_kaapana.instance_name] = client_dags
            just_all_dags = {**just_all_dags, **client_dags}
            # not all runner instances are remote instances --> set remote to False
            schemas["remote"] = False
        else:
            db_remote_kaapana_instance = crud.get_kaapana_instance(
                db, instance_name, remote=True
            )
            remote_allowed_dags = json.loads(
                db_remote_kaapana_instance.allowed_dags
            )  # w/o .keys() --> get dags incl. its meta information (not only dag_name)
            dags[db_remote_kaapana_instance.instance_name] = remote_allowed_dags
            just_all_dags = {**just_all_dags, **remote_allowed_dags}
    if (
        len(dags) > 1
    ):  # if multiple instances are selected -> find intersection of their allowed dags
        overall_allowed_dags = []
        for i in range(len(dags) - 1):
            if len(overall_allowed_dags) == 0:
                list1 = list(dags.values())[i]
                list2 = list(dags.values())[i + 1]
                overall_allowed_dags = list(set(list1) & set(list2))
            else:
                list1 = list(dags.values())[i]
                overall_allowed_dags = list(set(overall_allowed_dags) & set(list1))
        # get details of overall_allowed_dags
        overall_allowed_dags_datailed = {}
        for overall_allowed_dag in overall_allowed_dags:
            overall_allowed_dags_datailed[overall_allowed_dag] = just_all_dags[
                overall_allowed_dag
            ]
        dags = overall_allowed_dags_datailed
    elif (
        len(dags) == 1
    ):  # if just one instance is selected -> return (allowed) dags of this instance
        dags = list(dags.values())[0]

    if dag_id not in dags:
        raise HTTPException(
            status_code=404,
            detail=f"Dag {dag_id} is not part of the allowed dags, please add it!",
        )
    dag = dags[dag_id]
    schemas = dag["ui_forms"]

    # Datasets: Checking for datasets
    if (
        "data_form" in schemas
        and "properties" in schemas["data_form"]
        and "dataset_name" in schemas["data_form"]["properties"]
    ):
        db_client_kaapana = crud.get_kaapana_instance(
            db, remote=False
        )  # get client_instance
        datasets = {}
        for instance_name in filter_kaapana_instances.instance_names:
            # check if whether instance_name is client_instance --> datasets = crud.get_datasets(db, username=username)
            if db_client_kaapana.instance_name == instance_name:
                client_datasets = crud.get_datasets(
                    db, username=username
                )  # or rather get allowed_datasets of db_client_kaapana, but also a little bit unnecessary to restrict local datasets
                datasets[db_client_kaapana.instance_name] = [
                    ds.name for ds in client_datasets
                ]
            else:
                db_remote_kaapana_instance = crud.get_kaapana_instance(
                    db, instance_name, remote=True
                )
                remote_allowed_datasets = list(
                    json.loads(db_remote_kaapana_instance.allowed_datasets)
                )
                datasets[
                    db_remote_kaapana_instance.instance_name
                ] = remote_allowed_datasets
        if (
            len(datasets) > 1
        ):  # if multiple instances are selected -> find intersection of their allowed datasets
            overall_allowed_datasets = []
            for i in range(len(datasets) - 1):
                if len(overall_allowed_datasets) == 0:
                    list1 = list(datasets.values())[i]
                    list2 = list(datasets.values())[i + 1]
                    overall_allowed_datasets = list(set(list1) & set(list2))
                else:
                    list1 = list(datasets.values())[i]
                    overall_allowed_datasets = list(
                        set(overall_allowed_datasets) & set(list1)
                    )
            schemas["data_form"]["properties"]["dataset_name"]["oneOf"] = [
                {"const": d, "title": d} for d in overall_allowed_datasets
            ]
        elif (
            len(datasets) == 1
        ):  # if just one instance is selected -> return (allowed) datasets of this instance
            schemas["data_form"]["properties"]["dataset_name"]["oneOf"] = [
                {"const": d, "title": d} for d in list(datasets.values())[0]
            ]

    # logging.info(f"\n\nFinal Schema: \n{schemas}")
    return JSONResponse(content=schemas)


@router.get("/check-for-remote-updates")
def check_for_remote_updates(db: Session = Depends(get_db)):
    crud.get_remote_updates(db, periodically=False)
    return {f"Federated backend is up and running!"}


@router.post("/dataset", response_model=schemas.Dataset)
def create_dataset(
    request: Request,
    dataset: Union[schemas.DatasetCreate, None] = None,
    query: Union[str, None] = None,
    db: Session = Depends(get_db),
):
    query_dict = json.loads(query)
    if not dataset and query:
        dataset = schemas.DatasetCreate(
            name=query_dict["name"],
            identifiers=[
                d["_id"] for d in execute_opensearch_query(query_dict["query"])
            ],
        )
    dataset.username = request.headers["x-forwarded-preferred-username"]
    return crud.create_dataset(db=db, dataset=dataset)


@router.get("/dataset", response_model=schemas.Dataset)
async def get_dataset(name: str, db: Session = Depends(get_db)):
    return crud.get_dataset(db, name)


@router.get("/datasets", response_model=List[schemas.Dataset])
def get_datasets(
    request: Request,
    instance_name: str = None,
    limit: int = None,
    db: Session = Depends(get_db),
):
    return crud.get_datasets(
        db,
        instance_name,
        limit=limit,
        username=request.headers["x-forwarded-preferred-username"],
    )


@router.put("/dataset", response_model=schemas.Dataset)
def put_dataset(dataset: schemas.DatasetUpdate, db: Session = Depends(get_db)):
    return crud.update_dataset(db, dataset)


@router.delete("/dataset")
def delete_dataset(name: str, db: Session = Depends(get_db)):
    return crud.delete_dataset(db, name)


@router.delete("/datasets")
def delete_datasets(db: Session = Depends(get_db)):
    return crud.delete_datasets(db)


# create_experiment ; should replace and be sth like "def submit_workflow_json_schema()"
@router.post("/experiment", response_model=schemas.Experiment)   # also okay: schemas.ExperimentWithKaapanaInstance
def create_experiment(request: Request, json_schema_data: schemas.JsonSchemaData, db: Session = Depends(get_db)):
    
    # validate incoming json_schema_data
    try:
        jsonschema.validate(json_schema_data.json(), schema([schemas.JsonSchemaData]))
    except ValidationError as e:
        logging.error(f"JSON Schema is not valid for the Pydantic model. Error: {e}")
        raise HTTPException(status_code=400, detail="JSON Schema is not valid for the Pydantic model.")

    if json_schema_data.username is not None:
        username = json_schema_data.username
    elif "x-forwarded-preferred-username" in request.headers:
        username = request.headers["x-forwarded-preferred-username"]
        json_schema_data.username = username
    else:
        raise HTTPException(status_code=400, detail="A username has to be set when you submit a workflow schema, either as parameter or in the request!")

    db_client_kaapana = crud.get_kaapana_instance(db, remote=False)
    # if db_client_kaapana.instance_name in json_schema_data.instance_names:  # check or correct: if client_kaapana_instance in experiment's runner instances ...
    #     json_schema_data.remote = False                                     # ... set json_schema_data.remote to False

    conf_data = json_schema_data.conf_data

    if json_schema_data.federated:  # == True ;-)
        involved_instance_names = copy.deepcopy(json_schema_data.instance_names)
        involved_instance_names.extend(conf_data["external_schema_instance_names"])
    conf_data["experiment_form"] = {
        "username": username,
        "experiment_name": json_schema_data.experiment_name,
        "involved_instances": json_schema_data.instance_names
        if not json_schema_data.federated
        else involved_instance_names,  # instances on which experiment is created!
        "runner_instances": json_schema_data.instance_names,  # instances on which jobs of experiment are created!
    }

    if conf_data.get("data_form") and conf_data["data_form"].get("dataset_name"):
        db_dataset = crud.get_dataset(db, conf_data["data_form"]["dataset_name"])
        conf_data["data_form"].update(
            {
                "identifiers": json.loads(db_dataset.identifiers),
            }
        )

        data_form = conf_data["data_form"]
        dataset_limit = (
            int(data_form["dataset_limit"])
            if ("dataset_limit" in data_form and data_form["dataset_limit"] is not None)
            else None
        )
        single_execution = (
            "workflow_form" in conf_data
            and "single_execution" in conf_data["workflow_form"]
            and conf_data["workflow_form"]["single_execution"] is True
        )

    else:
        single_execution = False
        db_dataset = None

    # create an experiment with involved_instances=conf_data["experiment_form"]["involved_instances"] and add jobs to it
    experiment = schemas.ExperimentCreate(
        **{
            "experiment_name": json_schema_data.experiment_name,
            "username": username,
            "kaapana_instance_id": db_client_kaapana.id,
            # "experiment_jobs": db_jobs,
            "involved_kaapana_instances": conf_data["experiment_form"][
                "involved_instances"
            ],
            "dataset_name": db_dataset.name if db_dataset is not None else None,
        }
    )
    db_experiment = crud.create_experiment(db=db, experiment=experiment)

    # async function call to queue jobs and generate db_jobs + adding them to db_experiment
    # TODO moved methodcall outside of async framwork because our database implementation is not async compatible
    #asyncio.create_task(crud.queue_generate_jobs_and_add_to_exp(db, db_client_kaapana, db_experiment, json_schema_data, conf_data))
    crud.queue_generate_jobs_and_add_to_exp(db, db_client_kaapana, db_experiment, json_schema_data, conf_data)

    # directly return created db_experiment for fast feedback
    return db_experiment


# get_experiment
@router.get("/experiment", response_model=schemas.ExperimentWithKaapanaInstance)
def get_experiment(experiment_id: int = None, experiment_name: str = None, db: Session = Depends(get_db)):
    return crud.get_experiment(db, experiment_id, experiment_name)


# get_experiments
@router.get("/experiments", response_model=List[schemas.ExperimentWithKaapanaInstanceWithJobs]) # also okay: response_model=List[schemas.Experiment] ; List[schemas.ExperimentWithKaapanaInstance]
def get_experiments(request: Request, instance_name: str = None, involved_instance_name: str = None, experiment_job_id: int = None, limit: int = None, db: Session = Depends(get_db)):
    return crud.get_experiments(db, instance_name, involved_instance_name, experiment_job_id, limit=limit) # , username=request.headers["x-forwarded-preferred-username"]

# put/update_experiment
@router.put("/experiment", response_model=schemas.Experiment)
def put_experiment(experiment: schemas.ExperimentUpdate, db: Session = Depends(get_db)):
    if experiment.experiment_status == "abort":
        # iterate over experiment's jobs and execute crud.abort_job() and crud.update_job() and at the end also crud.update_experiment()
        db_experiment = crud.get_experiment(
            db, experiment.experiment_id
        )  # better call crud method directly instead of calling client.py's def get_experiment()
        for db_job in db_experiment.experiment_jobs:
            # compose a JobUpdate schema, set it's status to 'abort' and execute client.py's put_job()
            job = schemas.JobUpdate(
                **{
                    "job_id": db_job.id,
                    "status": "abort",
                    "description": "The job was aborted by the user!",
                }
            )

            # put_job(job, db)  # would be easier but doesn't work, so let's do it manually
            crud.abort_job(db, job, remote=False)
            job.status = "failed"
            crud.update_job(db, job, remote=False)  # update db_job to failed

        # update aborted experiment
        return crud.update_experiment(db, experiment)
    else:
        return crud.update_experiment(db, experiment)


# endpoint to update an experiment with additional experiment_jobs
@router.put("/experiment_jobs", response_model=schemas.Experiment)
def put_experiment_jobs(experiment: schemas.ExperimentUpdate, db: Session = Depends(get_db)):
    return crud.put_experiment_jobs(db, experiment)


# delete_experiment
@router.delete("/experiment")
def delete_experiment(experiment_id: int, db: Session = Depends(get_db)):
    return crud.delete_experiment(db, experiment_id)


# delete_experiments
@router.delete("/experiments")
def delete_experiments(db: Session = Depends(get_db)):
    return crud.delete_experiments(db)
