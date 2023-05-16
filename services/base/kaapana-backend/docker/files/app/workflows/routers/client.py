import copy
import json
import logging
import random
import string
import uuid
import shutil
from typing import List, Union
import asyncio
from threading import Thread

from pathlib import Path
import jsonschema
from app.datasets.utils import execute_opensearch_query
from app.dependencies import get_db
from app.workflows import crud
from app.workflows import schemas
from app.config import settings
from app.workflows.utils import HelperMinio
from app.workflows.utils import get_dag_list
from fastapi import APIRouter, Depends, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from pydantic.schema import schema
from sqlalchemy.orm import Session


logging.getLogger().setLevel(logging.DEBUG)

router = APIRouter(tags=["client"])

global minio_upload_mapping_dict
minio_upload_mapping_dict = dict()

UPLOAD_DIR = "/kaapana/mounted/minio/uploads"


@router.post("/minio-file-upload")
async def post_minio_file_upload(request: Request):
    form = await request.form()
    patch = str(uuid.uuid4())
    minio_upload_mapping_dict.update({patch: json.loads(form["filepond"])["filepath"]})
    # return Response(content=json.loads(form["filepond"])["filepath"])
    return Response(content=patch)


@router.patch("/minio-file-upload")
async def post_minio_file_upload(request: Request, patch: str):
    uoffset = request.headers.get("upload-offset", None)
    ulength = request.headers.get("upload-length", None)
    uname = request.headers.get("upload-name", None)
    fpath = Path(UPLOAD_DIR) / f"{patch}.tmp"
    with open(fpath, "ab") as f:
        async for chunk in request.stream():
            f.write(chunk)
    if ulength == str(fpath.stat().st_size):
        try:
            object_name = minio_upload_mapping_dict[patch]
            target_path = Path(UPLOAD_DIR) / object_name.strip("/")
            target_path.parents[0].mkdir(parents=True, exist_ok=True)
            logging.info(f"Moving file {fpath} to {target_path}")
            shutil.move(fpath, target_path)
            # Todo check if fput_objects also needs a long time... if not Minio file mount can be removed and UPLOAD_DIR might be /tmp
            # HelperMinio.minioClient.fput_object("uploads", minio_upload_mapping_dict[patch], fpath)
            logging.info(f"Successfully saved file {uname} to Minio")
            # fpath.unlink()
            filename = minio_upload_mapping_dict.pop(patch, "already deleted")
            return Response(f"Upload of {filename} succesful!")
        except Exception as e:
            logging.error(f"Failed to upload to Minio: {e}")
            if fpath.is_file():
                fpath.unlink()
            filename = minio_upload_mapping_dict.pop(patch, "already deleted")
            raise HTTPException(
                status_code=500, detail=f"Failed to upload {filename} to Minio: {e}"
            )
    return Response(patch)


@router.head("/minio-file-upload")
def head_minio_file_upload(request: Request, patch: str):
    uoffset = request.headers.get("upload-offset", None)
    ulength = request.headers.get("upload-length", None)
    uname = request.headers.get("upload-name", None)
    fpath = Path(UPLOAD_DIR) / f"{patch}.tmp"
    if fpath.is_file():
        offset = int(ulength) - fpath.stat().st_size
    else:
        offset = 0
    return Response(str(offset))


@router.delete("/minio-file-upload")
async def delete_minio_file_upload(request: Request):
    body = await request.body()
    patch = body.decode("utf-8")
    fpath = Path(UPLOAD_DIR) / f"{patch}.tmp"
    if fpath.is_file():
        fpath.unlink()
        filename = minio_upload_mapping_dict.pop(patch, "already deleted")
        return Response(f"Deleted {filename} succesfully!")
    else:
        return Response(
            "Only removing file in frontend. The file in the target location was already successfully uploaded"
        )


@router.post("/remote-kaapana-instance", response_model=schemas.KaapanaInstance)
def create_remote_kaapana_instance(
    remote_kaapana_instance: schemas.RemoteKaapanaInstanceCreate,
    db: Session = Depends(get_db),
):
    return crud.create_and_update_remote_kaapana_instance(
        db=db, remote_kaapana_instance=remote_kaapana_instance
    )


# @router.post("/client-kaapana-instance", response_model=schemas.KaapanaInstance)
# def create_client_kaapana_instance(
#     client_kaapana_instance: schemas.ClientKaapanaInstanceCreate,
#     db: Session = Depends(get_db),
# ):
#     return crud.create_and_update_client_kaapana_instance(
#         db=db, client_kaapana_instance=client_kaapana_instance
#     )


@router.put("/remote-kaapana-instance", response_model=schemas.KaapanaInstance)
def put_remote_kaapana_instance(
    remote_kaapana_instance: schemas.RemoteKaapanaInstanceCreate,
    db: Session = Depends(get_db),
):
    return crud.create_and_update_remote_kaapana_instance(
        db=db, remote_kaapana_instance=remote_kaapana_instance, action="update"
    )


@router.put("/client-kaapana-instance", response_model=schemas.KaapanaInstance)
def put_client_kaapana_instance(
    client_kaapana_instance: schemas.ClientKaapanaInstanceCreate,
    db: Session = Depends(get_db),
):
    return crud.create_and_update_client_kaapana_instance(
        db=db, client_kaapana_instance=client_kaapana_instance, action="update"
    )


@router.get("/kaapana-instance", response_model=schemas.KaapanaInstance)
def get_kaapana_instance(instance_name: str = None, db: Session = Depends(get_db)):
    return crud.get_kaapana_instance(db, instance_name)


@router.post("/get-kaapana-instances", response_model=List[schemas.KaapanaInstance])
def get_kaapana_instances(
    filter_kaapana_instances: schemas.FilterKaapanaInstances = None,
    db: Session = Depends(get_db),
):
    return crud.get_kaapana_instances(
        db, filter_kaapana_instances=filter_kaapana_instances
    )


@router.delete("/kaapana-instance")
def delete_kaapana_instance(kaapana_instance_id: int, db: Session = Depends(get_db)):
    return crud.delete_kaapana_instance(db, kaapana_instance_id=kaapana_instance_id)


@router.delete("/kaapana-instances")
def delete_kaapana_instances(db: Session = Depends(get_db)):
    return crud.delete_kaapana_instances(db)


@router.post("/job", response_model=schemas.JobWithKaapanaInstance)
# also okay: JobWithWorkflow
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


@router.get("/job", response_model=schemas.JobWithKaapanaInstance)
# also okay: JobWithWorkflow
def get_job(job_id: int = None, run_id: str = None, db: Session = Depends(get_db)):
    return crud.get_job(db, job_id, run_id)


@router.get("/jobs", response_model=List[schemas.JobWithWorkflowWithKaapanaInstance])
# also okay: JobWithWorkflow; JobWithKaapanaInstance
def get_jobs(
    instance_name: str = None,
    workflow_name: str = None,
    status: str = None,
    limit: int = None,
    db: Session = Depends(get_db),
):
    return crud.get_jobs(
        db, instance_name, workflow_name, status, remote=False, limit=limit
    )


@router.put("/job", response_model=schemas.JobWithWorkflow)
# changed JobWithKaapanaInstance to JobWithWorkflow
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


# dev feature: shouldn't be used in production
@router.delete("/job-force")
def delete_job_force(job_id: int, db: Session = Depends(get_db)):
    return crud.delete_job_force(db, job_id)


# needed?
@router.get("/dags")
async def dags(only_dag_names: bool = True):
    return get_dag_list(only_dag_names=only_dag_names)


@router.get("/get-job-taskinstances")
def get_job_taskinstances(job_id: int, db: Session = Depends(get_db)):
    return crud.get_job_taskinstances(db, job_id)


@router.post("/get-dags")
def get_dags(
    filter_kaapana_instances: schemas.FilterKaapanaInstances = None,
    db: Session = Depends(get_db),
):
    # if (filter_kaapana_instances.remote is False):  # necessary from old implementation to get dags in client instance view
    #     dags = get_dag_list(only_dag_names=True)
    #     return JSONResponse(content=dags)

    dags = {}
    for instance_name in filter_kaapana_instances.instance_names:
        db_kaapana_instance = crud.get_kaapana_instance(db, instance_name)
        if db_kaapana_instance.remote:
            remote_allowed_dags = list(
                json.loads(db_kaapana_instance.allowed_dags).keys()
            )
            dags[db_kaapana_instance.instance_name] = remote_allowed_dags
        else:
            dags[db_kaapana_instance.instance_name] = get_dag_list(
                only_dag_names=filter_kaapana_instances.only_dag_names,
                kind_of_dags=filter_kaapana_instances.kind_of_dags,
            )

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
def ui_form_schemas(
    request: Request,
    filter_kaapana_instances: schemas.FilterKaapanaInstances = None,
    db: Session = Depends(get_db),
):
    username = request.headers["x-forwarded-preferred-username"]
    dags = {}
    just_all_dags = {}
    for instance_name in filter_kaapana_instances.instance_names:
        db_kaapana_instance = crud.get_kaapana_instance(db, instance_name)
        if not db_kaapana_instance.remote:
            allowed_dags = get_dag_list(
                only_dag_names=False
            )  # get dags incl. its meta information (not only dag_name)
        else:
            allowed_dags = json.loads(
                db_kaapana_instance.allowed_dags
            )  # w/o .keys() --> get dags incl. its meta information (not only dag_name)
        dags[db_kaapana_instance.instance_name] = allowed_dags
        just_all_dags = {**just_all_dags, **allowed_dags}
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

    # Datasets: Checking for datasets
    # if (
    #     "data_form" in schemas
    #     and "properties" in schemas["data_form"]
    #     and "dataset_name" in schemas["data_form"]["properties"]
    # ):
    datasets = {}
    dataset_size = {}
    for instance_name in filter_kaapana_instances.instance_names:
        # check if whether instance_name is client_instance --> datasets = crud.get_datasets(db, username=username)
        db_kaapana_instance = crud.get_kaapana_instance(db, instance_name)
        if not db_kaapana_instance.remote:
            client_datasets = crud.get_datasets(
                db, username=username
            )  # or rather get allowed_datasets of db_client_kaapana, but also a little bit unnecessary to restrict local datasets
            allowed_dataset = [ds.name for ds in client_datasets]
            dataset_size = {
                ds.name: len(json.loads(ds.identifiers)) for ds in client_datasets
            }
        else:
            allowed_dataset = list(
                ds["name"] for ds in json.loads(db_kaapana_instance.allowed_datasets)
            )
        datasets[db_kaapana_instance.instance_name] = allowed_dataset

    if len(datasets) > 1:
        # if multiple instances are selected -> find intersection of their allowed datasets
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
        dataset_names = [{"const": d, "title": d} for d in overall_allowed_datasets]
    elif len(datasets) == 1:
        # if just one instance is selected -> return (allowed) datasets of this instance
        dataset_names = [
            {"const": d, "title": d + f" ({dataset_size[d]})"}
            for d in list(datasets.values())[0]
        ]

    schemas_dict = {}
    for dag_id, dag in dags.items():
        schemas = dag.get("ui_forms", {})
        # schemas = dag["ui_forms"]
        if (
            "data_form" in schemas
            and "properties" in schemas["data_form"]
            and "dataset_name" in schemas["data_form"]["properties"]
        ):
            if len(dataset_names) < 1:
                schemas["data_form"]["__emtpy__"] = "true"
            else:
                schemas["data_form"]["properties"]["dataset_name"][
                    "oneOf"
                ] = dataset_names
        schemas_dict[dag_id] = schemas
    # logging.info(f"\n\nFinal Schema: \n{schemas}")
    if filter_kaapana_instances.dag_id is None:
        return JSONResponse(content=schemas_dict)
    elif filter_kaapana_instances.dag_id in schemas_dict:
        return JSONResponse(
            content={
                filter_kaapana_instances.dag_id: schemas_dict[
                    filter_kaapana_instances.dag_id
                ]
            }
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Dag {dag_id} is not part of the dag list. In remote execution the issue might be that is it not part of the allowed dags, please add it!",
        )


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
    if not dataset and query:
        query_dict = json.loads(query)
        dataset = schemas.DatasetCreate(
            name=query_dict["name"],
            identifiers=[
                d["_id"] for d in execute_opensearch_query(query_dict["query"])
            ],
        )
    dataset.username = request.headers["x-forwarded-preferred-username"]
    return crud.create_dataset(db=db, dataset=dataset)


@router.get("/dataset", response_model=schemas.Dataset)
def get_dataset(name: str, db: Session = Depends(get_db)):
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


# create_workflow ; should replace and be sth like "def submit_workflow_json_schema()"
@router.post("/workflow", response_model=schemas.Workflow)
# also okay: schemas.WorkflowWithKaapanaInstance
# async def create_workflow(
def create_workflow(
    request: Request,
    json_schema_data: schemas.JsonSchemaData,
    db: Session = Depends(get_db),
):
    # validate incoming json_schema_data
    try:
        jsonschema.validate(json_schema_data.json(), schema([schemas.JsonSchemaData]))
    except ValidationError as e:
        logging.error(f"JSON Schema is not valid for the Pydantic model. Error: {e}")
        raise HTTPException(
            status_code=400, detail="JSON Schema is not valid for the Pydantic model."
        )

    # username
    if json_schema_data.username is not None:
        username = json_schema_data.username
    elif "x-forwarded-preferred-username" in request.headers:
        username = request.headers["x-forwarded-preferred-username"]
        json_schema_data.username = username
    else:
        raise HTTPException(
            status_code=400,
            detail="A username has to be set when you submit a workflow schema, either as parameter or in the request!",
        )

    db_client_kaapana = crud.get_kaapana_instance(db)
    # if db_client_kaapana.instance_name in json_schema_data.instance_names:  # check or correct: if client_kaapana_instance in workflow's runner instances ...
    #     json_schema_data.remote = False                                     # ... set json_schema_data.remote to False

    # conf_data = json_schema_data.conf_data

    # generate random and unique workflow id
    characters = string.ascii_uppercase + string.ascii_lowercase + string.digits
    workflow_id = "".join(random.choices(characters, k=6))
    # append workflow_id to workflow_name
    workflow_name = workflow_id + "-" + json_schema_data.workflow_name

    # TODO adapt involed instances per job?
    if json_schema_data.federated:  # == True ;-)
        involved_instance_names = copy.deepcopy(json_schema_data.instance_names)
        involved_instance_names.extend(
            json_schema_data.conf_data["external_schema_instance_names"]
        )
    if not "workflow_form" in json_schema_data.conf_data:
        json_schema_data.conf_data["workflow_form"] = {}
    json_schema_data.conf_data["workflow_form"].update(
        {
            "username": username,
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "involved_instances": json_schema_data.instance_names
            if json_schema_data.federated == False
            else involved_instance_names,  # instances on which workflow is created!
            "runner_instances": json_schema_data.instance_names,  # instances on which jobs of workflow are created!
        }
    )

    # create an workflow with involved_instances=conf_data["workflow_form"]["involved_instances"] and add jobs to it
    workflow = schemas.WorkflowCreate(
        **{
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "username": username,
            "kaapana_instance_id": db_client_kaapana.id,
            # "workflow_jobs": db_jobs,
            "involved_kaapana_instances": json_schema_data.conf_data["workflow_form"][
                "involved_instances"
            ],
            "federated": json_schema_data.federated,
        }
    )
    db_workflow = crud.create_workflow(db=db, workflow=workflow)

    # async function call to queue jobs and generate db_jobs + adding them to db_workflow
    # TODO moved methodcall outside of async framwork because our database implementation is not async compatible
    # asyncio.create_task(
    #     crud.queue_generate_jobs_and_add_to_workflow(db, db_workflow, json_schema_data)
    #     )

    if (
        db_client_kaapana.instance_name
        not in json_schema_data.conf_data["workflow_form"]["involved_instances"]
        or len(json_schema_data.conf_data["workflow_form"]["involved_instances"]) > 1
    ):
        # sync solution for remote or any federated workflows
        crud.queue_generate_jobs_and_add_to_workflow(db, db_workflow, json_schema_data)
    else:
        # solution in additional thread for purely local workflows (these are probably also the only one which are conducted at large scale)
        Thread(
            target=crud.queue_generate_jobs_and_add_to_workflow,
            args=(db, db_workflow, json_schema_data),
        ).start()

    # directly return created db_workflow for fast feedback
    return db_workflow


# get_workflow
@router.get("/workflow", response_model=schemas.WorkflowWithKaapanaInstance)
def get_workflow(
    workflow_id: str = None,
    workflow_name: str = None,
    dag_id: str = None,
    db: Session = Depends(get_db),
):
    return crud.get_workflow(db, workflow_id, workflow_name, dag_id)


# get_workflows
@router.get(
    "/workflows", response_model=List[schemas.WorkflowWithKaapanaInstanceWithJobs]
)
# also okay: response_model=List[schemas.Workflow] ; List[schemas.WorkflowWithKaapanaInstance]
def get_workflows(
    request: Request,
    instance_name: str = None,
    involved_instance_name: str = None,
    workflow_job_id: int = None,
    limit: int = None,
    db: Session = Depends(get_db),
):
    return crud.get_workflows(
        db, instance_name, involved_instance_name, workflow_job_id, limit=limit
    )  # , username=request.headers["x-forwarded-preferred-username"]


# put/update_workflow
@router.put("/workflow", response_model=schemas.Workflow)
def put_workflow(workflow: schemas.WorkflowUpdate, db: Session = Depends(get_db)):
    if workflow.workflow_status == "abort":
        # iterate over workflow's jobs and execute crud.abort_job() and crud.update_job() and at the end also crud.update_workflow()
        db_workflow = crud.get_workflow(db, workflow.workflow_id)
        for db_job in db_workflow.workflow_jobs:
            # if (not db_workflow.federated and not db_job.kaapana_instance.remote) or (db_workflow.federated and "external_schema_federated_form" in db_job.conf_data):
            if not db_job.kaapana_instance.remote:
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

        # update aborted workflow
        return crud.update_workflow(db, workflow)
    elif (
        workflow.workflow_status == "scheduled"
        or workflow.workflow_status == "confirmed"
    ):
        return crud.update_workflow(db, workflow)
    else:
        raise HTTPException(
            status_code=405,
            detail=f"Updating worklfow with status '{workflow.workflow_status}' not supported!",
        )


# endpoint to update an workflow with additional workflow_jobs
@router.put(
    "/workflow_jobs", response_model=List[schemas.Job]
)  # , response_model=schemas.WorkflowWithJobs) # , response_model=schemas.Workflow)
def put_workflow_jobs(
    json_schema_data: schemas.JsonSchemaData,
    # workflow_id: str=None,
    db: Session = Depends(get_db),
):
    db_workflow = crud.get_workflow(db, workflow_id=json_schema_data.workflow_id)
    r = crud.queue_generate_jobs_and_add_to_workflow(db, db_workflow, json_schema_data)
    resp = r["jobs"]
    return resp


# delete_workflow
@router.delete("/workflow")
def delete_workflow(workflow_id: str, db: Session = Depends(get_db)):
    return crud.delete_workflow(db, workflow_id)


# delete_workflows
@router.delete("/workflows")
def delete_workflows(db: Session = Depends(get_db)):
    return crud.delete_workflows(db)
