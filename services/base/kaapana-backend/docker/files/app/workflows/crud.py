import json
import os
import logging
import traceback
import uuid
import copy
from typing import List
import datetime
import string
import random

import requests
from cryptography.fernet import Fernet
from fastapi import HTTPException, Response
from psycopg2.errors import UniqueViolation
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from urllib3.util import Timeout

from app.config import settings
from . import models, schemas
from .schemas import DatasetCreate
from .utils import (
    execute_job_airflow,
    abort_job_airflow,
    get_dagrun_tasks_airflow,
    get_dagrun_details_airflow,
    get_dagruns_airflow,
    check_dag_id_and_dataset,
    get_utc_timestamp,
    HelperMinio,
    get_dag_list,
    raise_kaapana_connection_error,
    requests_retry_session,
)

logging.getLogger().setLevel(logging.INFO)

TIMEOUT_SEC = 5
TIMEOUT = Timeout(TIMEOUT_SEC)


def delete_kaapana_instance(db: Session, kaapana_instance_id: int):
    db_kaapana_instance = (
        db.query(models.KaapanaInstance).filter_by(id=kaapana_instance_id).first()
    )
    if not db_kaapana_instance:
        raise HTTPException(status_code=404, detail="Kaapana instance not found")
    db.delete(db_kaapana_instance)
    db.commit()
    return {"ok": True}


def delete_kaapana_instances(db: Session):
    db.query(models.KaapanaInstance).delete()
    db.commit()
    return {"ok": True}


def get_kaapana_instance(db: Session, instance_name: str = None):
    # db_kaapana_instance = (db.query(models.KaapanaInstance)
    #     .filter_by(instance_name=instance_name or settings.instance_name)
    #     .first())
    # # workaround that backend isn't crashing if remote kaapana instance is not reachable
    # db.close()
    # return db_kaapana_instance
    return (
        db.query(models.KaapanaInstance)
        .filter_by(instance_name=instance_name or settings.instance_name)
        .first()
    )


def get_kaapana_instances(
    db: Session, filter_kaapana_instances: schemas.FilterKaapanaInstances = None
):
    if filter_kaapana_instances is not None and filter_kaapana_instances.instance_names:
        # db_kaapana_instances = (db.query(models.KaapanaInstance)
        #                         .filter(models.KaapanaInstance.instance_name.in_(
        #                             filter_kaapana_instances.instance_names),
        #                         ).all()
        #                         )
        # db.close()
        # return db_kaapana_instances
        return (
            db.query(models.KaapanaInstance)
            .filter(
                models.KaapanaInstance.instance_name.in_(
                    filter_kaapana_instances.instance_names
                ),
            )
            .all()
        )
    elif (
        filter_kaapana_instances is not None
        and filter_kaapana_instances.dag_id is not None
    ):
        # db_kaapana_instances = (db.query(models.KaapanaInstance)
        #                         .filter(models.KaapanaInstance.allowed_dags.contains(
        #                             filter_kaapana_instances.dag_id),
        #                         ).all()
        #                         )
        # db.close()
        # return db_kaapana_instances
        return (
            db.query(models.KaapanaInstance)
            .filter(
                models.KaapanaInstance.allowed_dags.contains(
                    filter_kaapana_instances.dag_id
                ),
            )
            .all()
        )
    elif (
        filter_kaapana_instances is not None
        and filter_kaapana_instances.instance_names
        and filter_kaapana_instances.dag_id is not None
    ):
        # db_kaapana_instances = (db.query(models.KaapanaInstance)
        #                         .filter(models.KaapanaInstance.allowed_dags.contains(
        #                                 filter_kaapana_instances.dag_id),
        #                             models.KaapanaInstance.instance_name.in_(
        #                                 filter_kaapana_instances.instance_names),
        #                         ).all()
        #                         )
        # db.close()
        # return db_kaapana_instances
        return (
            db.query(models.KaapanaInstance)
            .filter(
                models.KaapanaInstance.allowed_dags.contains(
                    filter_kaapana_instances.dag_id
                ),
                models.KaapanaInstance.instance_name.in_(
                    filter_kaapana_instances.instance_names
                ),
            )
            .all()
        )
    else:
        # db_kaapana_instances = (db.query(models.KaapanaInstance)
        #     .order_by(models.KaapanaInstance.remote, models.KaapanaInstance.instance_name)
        #     .all()
        # )
        # db.close()
        # return db_kaapana_instances
        return (
            db.query(models.KaapanaInstance)
            .order_by(
                models.KaapanaInstance.remote, models.KaapanaInstance.instance_name
            )
            .all()
        )


def create_and_update_client_kaapana_instance(
    db: Session,
    client_kaapana_instance: schemas.ClientKaapanaInstanceCreate,
    action="create",
):
    def _get_fernet_key(fernet_encrypted):
        if fernet_encrypted is True:
            return Fernet.generate_key().decode()
        else:
            return "deactivated"

    utc_timestamp = get_utc_timestamp()

    db_client_kaapana_instance = get_kaapana_instance(db)
    if action == "create":
        if db_client_kaapana_instance:
            raise HTTPException(
                status_code=400, detail="Kaapana instance already exists!"
            )

    if action == "create":
        db_client_kaapana_instance = models.KaapanaInstance(
            instance_name=settings.instance_name,
            token=str(uuid.uuid4()),
            protocol="https",
            host=settings.hostname,
            port=int(os.getenv("HTTPS_PORT", 443)),
            ssl_check=client_kaapana_instance.ssl_check,
            fernet_key=_get_fernet_key(client_kaapana_instance.fernet_encrypted),
            encryption_key=Fernet.generate_key().decode(),
            remote=False,
            time_created=utc_timestamp,
            time_updated=utc_timestamp,
            automatic_update=client_kaapana_instance.automatic_update or False,
            automatic_workflow_execution=client_kaapana_instance.automatic_workflow_execution
            or False,
        )
    elif action == "update":
        allowed_dags = json.dumps(
            get_dag_list(
                only_dag_names=False,
                filter_allowed_dags=client_kaapana_instance.allowed_dags,
            )
        )

        fernet = Fernet(db_client_kaapana_instance.encryption_key)
        allowed_datasets = []
        for dataset_name in client_kaapana_instance.allowed_datasets:
            db_dataset = get_dataset(db, name=dataset_name, raise_if_not_existing=False)
            if db_dataset:
                dataset = schemas.AllowedDatasetCreate(**(db_dataset).__dict__).dict()
                if "identifiers" in dataset:
                    dataset["identifiers"] = [
                        fernet.encrypt(identifier.encode()).decode()
                        for identifier in dataset["identifiers"]
                    ]
                allowed_datasets.append(dataset)
        allowed_datasets = json.dumps(allowed_datasets)

        db_client_kaapana_instance.instance_name = (settings.instance_name,)
        db_client_kaapana_instance.time_updated = utc_timestamp
        if (
            db_client_kaapana_instance.fernet_key == "deactivated"
            and client_kaapana_instance.fernet_encrypted is True
        ):
            db_client_kaapana_instance.fernet_key = _get_fernet_key(
                client_kaapana_instance.fernet_encrypted
            )
        elif (
            db_client_kaapana_instance.fernet_key != "deactivated"
            and client_kaapana_instance.fernet_encrypted is False
        ):
            db_client_kaapana_instance.fernet_key = "deactivated"
        db_client_kaapana_instance.ssl_check = client_kaapana_instance.ssl_check
        db_client_kaapana_instance.allowed_dags = allowed_dags
        db_client_kaapana_instance.allowed_datasets = allowed_datasets
        db_client_kaapana_instance.automatic_update = (
            client_kaapana_instance.automatic_update or False
        )
        db_client_kaapana_instance.automatic_workflow_execution = (
            client_kaapana_instance.automatic_workflow_execution or False
        )
    else:
        raise NameError("action must be one of create, update")

    logging.debug("Updating Kaapana Instance successful!")

    db.add(db_client_kaapana_instance)
    db.commit()
    db.refresh(db_client_kaapana_instance)
    return db_client_kaapana_instance


def create_and_update_remote_kaapana_instance(
    db: Session,
    remote_kaapana_instance: schemas.RemoteKaapanaInstanceCreate,
    action="create",
):
    utc_timestamp = get_utc_timestamp()
    db_remote_kaapana_instance = get_kaapana_instance(
        db, remote_kaapana_instance.instance_name
    )
    if action == "create":
        if db_remote_kaapana_instance:
            raise HTTPException(
                status_code=400, detail="Kaapana instance already exists!"
            )
    if action == "create":
        db_remote_kaapana_instance = models.KaapanaInstance(
            instance_name=remote_kaapana_instance.instance_name,
            token=remote_kaapana_instance.token,
            protocol="https",
            host=remote_kaapana_instance.host,
            port=remote_kaapana_instance.port,
            ssl_check=remote_kaapana_instance.ssl_check,
            fernet_key=remote_kaapana_instance.fernet_key or "deactivated",
            remote=True,
            time_created=utc_timestamp,
            # time_updated=utc_timestamp,
            time_updated=datetime.datetime.min,
        )
    elif action == "update":
        db_remote_kaapana_instance.token = remote_kaapana_instance.token
        db_remote_kaapana_instance.port = remote_kaapana_instance.port
        db_remote_kaapana_instance.ssl_check = remote_kaapana_instance.ssl_check
        db_remote_kaapana_instance.fernet_key = (
            remote_kaapana_instance.fernet_key or "deactivated"
        )
        db_remote_kaapana_instance.time_updated = utc_timestamp
    elif action == "external_update":
        logging.debug(
            f"Externally updating with db_remote_kaapana_instance: {db_remote_kaapana_instance}"
        )
        if db_remote_kaapana_instance:
            db_remote_kaapana_instance.allowed_dags = json.dumps(
                remote_kaapana_instance.allowed_dags
            )
            db_remote_kaapana_instance.allowed_datasets = json.dumps(
                remote_kaapana_instance.allowed_datasets
            )
            db_remote_kaapana_instance.automatic_update = (
                remote_kaapana_instance.automatic_update or False
            )
            db_remote_kaapana_instance.automatic_workflow_execution = (
                remote_kaapana_instance.automatic_workflow_execution or False
            )
            db_remote_kaapana_instance.time_updated = utc_timestamp
        else:
            return Response(
                "Your instance name differs from the remote instance name!", 200
            )
    else:
        raise NameError("action must be one of create, update, external_update")
    db.add(db_remote_kaapana_instance)
    db.commit()
    db.refresh(db_remote_kaapana_instance)
    return db_remote_kaapana_instance


def create_job(db: Session, job: schemas.JobCreate, service_job: str = False):
    db_kaapana_instance = (
        db.query(models.KaapanaInstance).filter_by(id=job.kaapana_instance_id).first()
    )
    if not db_kaapana_instance:
        raise HTTPException(status_code=404, detail="Kaapana instance not found")

    # if (
    #     db_kaapana_instance.remote is True
    #     and "federated_form" in job.conf_data
    #     and (
    #         "federated_dir" in job.conf_data["federated_form"]
    #         and "federated_bucket" in job.conf_data["federated_form"]
    #         and "federated_operators" in job.conf_data["federated_form"]
    #     )
    # ):
    if "federated_form" in job.conf_data and (
        "federated_dir" in job.conf_data["federated_form"]
        and "federated_bucket" in job.conf_data["federated_form"]
        and "federated_operators" in job.conf_data["federated_form"]
    ):
        minio_urls = HelperMinio.add_minio_urls(
            job.conf_data["federated_form"], db_kaapana_instance.instance_name
        )
        job.conf_data["federated_form"]["minio_urls"] = minio_urls

    utc_timestamp = get_utc_timestamp()

    db_job = models.Job(
        # id = job.id,    # not sure if this shouldn't be set automatically
        conf_data=json.dumps(job.conf_data),
        time_created=utc_timestamp,
        time_updated=utc_timestamp,
        external_job_id=job.external_job_id,
        username=job.username,
        dag_id=job.dag_id,
        # run_id only for service-jobs which are already running in airflow w/known run_id before corresponding db_job is created
        run_id=job.run_id,
        kaapana_id=job.kaapana_instance_id,
        owner_kaapana_instance_name=job.owner_kaapana_instance_name,
        # replaced addressed_kaapana_instance_name w/ owner_kaapana_instance_name or None
        status=job.status,
        automatic_execution=job.automatic_execution,
        service_job=job.service_job,
    )

    db_kaapana_instance.jobs.append(db_job)
    db.add(db_kaapana_instance)
    try:
        db.commit()  # writing, if kaapana_id and external_job_id already exists will fail due to duplicate error
    except IntegrityError as e:
        assert isinstance(e.orig, UniqueViolation)  # proves the original exception
        return (
            db.query(models.Job)
            .filter_by(
                external_job_id=db_job.external_job_id,
                owner_kaapana_instance_name=db_job.owner_kaapana_instance_name,
            )
            .first()
        )
    # update_external_job() updates from remote the job on client instance
    update_external_job(db, db_job)
    db.refresh(db_job)

    if (
        db_kaapana_instance.remote is False
        and service_job is False
        and db_job.automatic_execution is True
    ):
        # iff db_kp_i of db_job is the local one, then proceed and schedule the created "queued" job on local airflow via def update_job()
        job = schemas.JobUpdate(
            **{
                "job_id": db_job.id,
                "status": "scheduled",
                "description": "The workflow was triggered!",
            }
        )
        update_job(db, job, remote=False)

    return db_job


def get_job(db: Session, job_id: int = None, run_id: str = None):
    if job_id is not None:
        db_job = db.query(models.Job).filter_by(id=job_id).first()
    elif run_id is not None:
        db_job = db.query(models.Job).filter_by(run_id=run_id).first()
    # if not db_job:
    else:
        logging.warning(
            f"No job found in db with job_id={job_id}, run_id={run_id} --> will return None"
        )
        raise HTTPException(status_code=404, detail="Job not found")
        return None

    return db_job


def delete_job(db: Session, job_id: int, remote: bool = True):
    db_job = get_job(db, job_id)
    if (db_job.workflow.kaapana_instance.remote != remote) and db_job.status not in [
        "queued",
        "finished",
        "failed",
    ]:
        raise HTTPException(
            status_code=401,
            detail="You are not allowed to delete this job, since its on the client site",
        )
    delete_external_job(db, db_job)
    db.delete(db_job)
    db.commit()
    return {"ok": True}


def delete_jobs(db: Session):
    # Todo add remote job deletion
    db.query(models.Job).delete()
    db.commit()
    return {"ok": True}


# dev feature: shouldn't be used in production
def delete_job_force(db: Session, job_id: int):
    db_job = get_job(db, job_id)
    db.delete(db_job)
    db.commit()
    return {"ok": True}


def get_jobs(
    db: Session,
    instance_name: str = None,
    workflow_name: str = None,
    status: str = None,
    remote: bool = True,
    limit=None,
):
    if instance_name is not None and status is not None:
        return (
            db.query(models.Job)
            .filter_by(status=status)
            .join(models.Job.kaapana_instance, aliased=True)
            .filter_by(instance_name=instance_name)
            .order_by(desc(models.Job.time_updated))
            .limit(limit)
            .all()
        )  # same as org but w/o filtering by remote
    elif workflow_name is not None and status is not None:
        return (
            db.query(models.Job)
            .filter_by(status=status)
            .join(models.Job.workflow, aliased=True)
            .filter_by(workflow_name=workflow_name)
            .order_by(desc(models.Job.time_updated))
            .limit(limit)
            .all()
        )
    elif instance_name is not None:
        return (
            db.query(models.Job)
            .join(models.Job.kaapana_instance, aliased=True)
            .filter_by(instance_name=instance_name)
            .order_by(desc(models.Job.time_updated))
            .limit(limit)
            .all()
        )  # same as org but w/o filtering by remote
    elif workflow_name is not None:
        return (
            db.query(models.Job)
            .join(models.Job.workflow, aliased=True)
            .filter_by(workflow_name=workflow_name)
            .order_by(desc(models.Job.time_updated))
            .limit(limit)
            .all()
        )
    elif status is not None:
        return (
            db.query(models.Job)
            .filter_by(status=status)
            .join(models.Job.kaapana_instance, aliased=True)
            .order_by(desc(models.Job.time_updated))
            .limit(limit)
            .all()
        )  # same as org but w/o filtering by remote
    else:
        return (
            db.query(models.Job)
            .join(models.Job.workflow, aliased=True)
            .join(models.Workflow.kaapana_instance, aliased=True)
            .filter_by(remote=remote)
            .order_by(desc(models.Job.time_updated))
            .limit(limit)
            .all()
        )
        # explanation: db.query(models.Job) returns a Query object; .join() creates more narrow Query objects ; filter_by() applies the filter criterion to the remaining Query (source: https://docs.sqlalchemy.org/en/14/orm/query.html#sqlalchemy.orm.Query)


def update_job(db: Session, job=schemas.JobUpdate, remote: bool = True):
    utc_timestamp = get_utc_timestamp()

    db_job = get_job(db, job.job_id, job.run_id)

    # update jobs of own db which are remotely executed (def update_job() is in this case called from remote.py's def put_job())
    if db_job.kaapana_instance.remote:
        db_job.status = job.status

    if job.status == "scheduled" and db_job.kaapana_instance.remote == False:
        # or (job.status == 'failed'); status='scheduled' for restarting, status='failed' for aborting
        conf_data = json.loads(db_job.conf_data)
        conf_data["client_job_id"] = db_job.id
        dag_id_and_dataset = check_dag_id_and_dataset(
            db_job.kaapana_instance,
            conf_data,
            db_job.dag_id,
            db_job.owner_kaapana_instance_name,
        )
        if dag_id_and_dataset is not None:
            job.status = "failed"
            job.description = dag_id_and_dataset
        else:
            airflow_execute_resp = execute_job_airflow(conf_data, db_job)
            airflow_execute_resp_text = json.loads(airflow_execute_resp.text)
            dag_id = airflow_execute_resp_text["message"][1]["dag_id"]
            dag_run_id = airflow_execute_resp_text["message"][1]["run_id"]
            db_job.dag_id = dag_id  # write directly to db_job to already use db_job.dag_id before db commit
            db_job.run_id = dag_run_id

    # check state and run_id for created or queued, scheduled, running jobs on local instance
    if db_job.run_id is not None and db_job.kaapana_instance.remote == False:
        # ask here first time Airflow for job status (explicit w/ job_id) via kaapana_api's def dag_run_status()
        airflow_details_resp = get_dagrun_details_airflow(db_job.dag_id, db_job.run_id)
        if not airflow_details_resp.ok:
            # request to airflow results in response != 200 ==> error!
            # set db_job manually to deleted
            logging.error(
                f"Couldn't find db_job {db_job.id} in airlfow ==> will set db_job to 'deleted'."
            )
            db_job.status = "deleted"
            db_job.time_updated = utc_timestamp
            db.commit()
            db.refresh(db_job)
            raise_kaapana_connection_error(airflow_details_resp)
            return db_job
        airflow_details_resp_text = json.loads(airflow_details_resp.text)
        # update db_job w/ job's real state and run_id fetched from Airflow ; special case for status = "success"
        db_job.status = (
            "finished"
            if airflow_details_resp_text["state"] == "success"
            else airflow_details_resp_text["state"]
        )
        db_job.run_id = airflow_details_resp_text["run_id"]

    # if (db_job.kaapana_instance.remote != remote) and db_job.status not in [
    #     "queued",
    #     "finished",
    #     "failed",
    # ]:
    #     raise HTTPException(
    #         status_code=401,
    #         detail="You are not allowed to update this job, since its on the client site",
    #     )

    if job.run_id is not None:
        db_job.run_id = job.run_id
    if job.description is not None:
        db_job.description = job.description
    db_job.time_updated = utc_timestamp
    update_external_job(db, db_job)
    db.commit()
    db.refresh(db_job)

    return db_job


def abort_job(db: Session, job=schemas.JobUpdate, remote: bool = True):
    utc_timestamp = get_utc_timestamp()
    db_job = get_job(db, job.job_id)

    airflow_details_resp = get_dagrun_details_airflow(db_job.dag_id, db_job.run_id)
    if airflow_details_resp.status_code == 200:
        # repsonse.text of abort_job_airflow usused in backend but might be valuable for debugging
        abort_job_airflow(db_job.dag_id, db_job.run_id, "failed")
        # abort_job_airflow(airflow_details_resp.text["dag_id"], airflow_details_resp.text["run_id"], "failed") # db_job.status
    else:
        logging.error(
            f"No dag_run in Airflow with dag_id '{db_job.dag_id}' and run_id '{db_job.run_id}'."
        )


def get_job_taskinstances(db: Session, job_id: int = None):
    db_job = get_job(db, job_id)  # query job by job_id
    response = get_dagrun_tasks_airflow(
        db_job.dag_id, db_job.run_id
    )  # get task_instances w/ states via dag_id and run_id

    # parse received response
    response_text = json.loads(response.text)
    ti_state_dict = eval(
        response_text["message"][0]
    )  # convert dict-like strings to dicts
    ti_exdate_dict = eval(response_text["message"][1])

    # compose dict in style {"task_instance": ["execution_time", "state"]}
    tis_n_state = {}
    for key in ti_state_dict:
        time_n_state = [ti_exdate_dict[key], ti_state_dict[key]]
        tis_n_state[key] = time_n_state

    return tis_n_state


def sync_client_remote(
    db: Session,
    remote_kaapana_instance: schemas.RemoteKaapanaInstanceUpdateExternal,
    instance_name: str = None,
    status: str = None,
):
    db_client_kaapana = get_kaapana_instance(db)

    create_and_update_remote_kaapana_instance(
        db=db, remote_kaapana_instance=remote_kaapana_instance, action="external_update"
    )

    # get jobs on client_kaapana_instance with instance="instance_name" and status="status"
    db_outgoing_jobs = get_jobs(
        db, instance_name=instance_name, status=status, remote=True
    )
    # outgoing_jobs = [schemas.Job(**job.__dict__).dict() for job in db_outgoing_jobs]

    # get workflows on client_kaapana_instance which contain outgoing_jobs
    outgoing_jobs = []
    outgoing_workflows = []
    for db_outgoing_job in db_outgoing_jobs:
        if db_outgoing_job.kaapana_instance.id == db_client_kaapana.id:
            continue
        outgoing_jobs.append(schemas.Job(**db_outgoing_job.__dict__).dict())

        db_outgoing_workflow = get_workflows(db, workflow_job_id=db_outgoing_job.id)
        outgoing_workflow = (
            [
                schemas.Workflow(**workflow.__dict__).dict()
                for workflow in db_outgoing_workflow
            ][0]
            if len(db_outgoing_workflow) > 0
            else None
        )
        if outgoing_workflow is not None:
            outgoing_workflows.append(outgoing_workflow)

    logging.debug(f"SYNC_CLIENT_REMOTE outgoing_jobs: {outgoing_jobs}")
    logging.debug(f"SYNC_CLIENT_REMOTE outgoing_workflows: {outgoing_workflows}")

    update_remote_instance_payload = {
        "instance_name": db_client_kaapana.instance_name,
        "allowed_dags": json.loads(db_client_kaapana.allowed_dags),
        "allowed_datasets": json.loads(db_client_kaapana.allowed_datasets),
        "automatic_update": db_client_kaapana.automatic_update,
        "automatic_workflow_execution": db_client_kaapana.automatic_workflow_execution,
    }
    return {
        "incoming_jobs": outgoing_jobs,
        "incoming_workflows": outgoing_workflows,
        "update_remote_instance_payload": update_remote_instance_payload,
    }


def delete_external_job(db: Session, db_job):
    if db_job.external_job_id is not None:
        db_remote_kaapana_instance = get_kaapana_instance(
            db, instance_name=db_job.owner_kaapana_instance_name
        )
        params = {
            "job_id": db_job.external_job_id,
        }

        # if db_remote_kaapana_instance.instance_name == settings.instance_name:
        #     delete_job(db, **params)
        # else:
        remote_backend_url = f"{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/kaapana-backend/remote"
        with requests.Session() as s:
            r = requests_retry_session(session=s).delete(
                f"{remote_backend_url}/job",
                verify=db_remote_kaapana_instance.ssl_check,
                params=params,
                headers={
                    "FederatedAuthorization": f"{db_remote_kaapana_instance.token}"
                },
                timeout=TIMEOUT,
            )
        if r.status_code == 404:
            logging.warning(f"External job {db_job.external_job_id} does not exist")
        else:
            raise_kaapana_connection_error(r)
            logging.error(r.json())


def update_external_job(db: Session, db_job):
    if db_job.external_job_id is not None:
        db_remote_kaapana_instance = get_kaapana_instance(
            db, instance_name=db_job.owner_kaapana_instance_name
        )
        if db_job.status != "queued":
            # only update status to owner instance if not "queued" otherwise job will be again from owner_instance by this local instance
            payload = {
                "job_id": db_job.external_job_id,
                "run_id": db_job.run_id,
                "status": db_job.status,
                "description": db_job.description,
            }

            # if db_remote_kaapana_instance.instance_name == settings.instance_name:
            #     update_job(db, schemas.JobUpdate(**payload))
            # else:
            remote_backend_url = f"{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/kaapana-backend/remote"
            with requests.Session() as s:
                r = requests_retry_session(session=s).put(
                    f"{remote_backend_url}/job",
                    verify=db_remote_kaapana_instance.ssl_check,
                    json=payload,
                    headers={
                        "FederatedAuthorization": f"{db_remote_kaapana_instance.token}"
                    },
                    timeout=TIMEOUT,
                )
            if r.status_code == 404:
                logging.warning(f"External job {db_job.external_job_id} does not exist")
            elif r.status_code != 200:
                logging.error("Error in CRUD def update_external_job()")
                raise_kaapana_connection_error(r)
                logging.error(r.json())
            raise_kaapana_connection_error(r)
            # else:
            #     logging.error("Error in CRUD def update_external_job()")
            #     raise_kaapana_connection_error(r)
            #     logging.error(r.json())


def get_remote_updates(db: Session, periodically=False):
    db_client_kaapana = get_kaapana_instance(db)
    if periodically is True and db_client_kaapana.automatic_update is False:
        return
    db_kaapana_instances = get_kaapana_instances(db)
    for db_remote_kaapana_instance in db_kaapana_instances:
        if not db_remote_kaapana_instance.remote:
            # Skipping locally running jobs
            continue
        update_remote_instance_payload = {
            "instance_name": db_client_kaapana.instance_name,
            "allowed_dags": json.loads(db_client_kaapana.allowed_dags),
            "allowed_datasets": json.loads(db_client_kaapana.allowed_datasets),
            "automatic_update": db_client_kaapana.automatic_update,
            "automatic_workflow_execution": db_client_kaapana.automatic_workflow_execution,
        }

        job_params = {
            "instance_name": db_client_kaapana.instance_name,
            "status": "queued",
        }
        remote_backend_url = f"{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/kaapana-backend/remote"
        with requests.Session() as s:
            r = requests_retry_session(session=s).put(
                f"{remote_backend_url}/sync-client-remote",
                params=job_params,
                json=update_remote_instance_payload,
                verify=db_remote_kaapana_instance.ssl_check,
                headers={
                    "FederatedAuthorization": f"{db_remote_kaapana_instance.token}"
                },
                timeout=TIMEOUT,
            )
        if r.status_code != 200:
            logging.warning(
                f"Warning!!! We could not reach the following backend {db_remote_kaapana_instance.host}"
            )
            continue
        raise_kaapana_connection_error(r)
        incoming_data = r.json()

        incoming_jobs = incoming_data["incoming_jobs"]
        incoming_workflows = incoming_data["incoming_workflows"]
        remote_kaapana_instance = schemas.RemoteKaapanaInstanceUpdateExternal(
            **incoming_data["update_remote_instance_payload"]
        )

        create_and_update_remote_kaapana_instance(
            db=db,
            remote_kaapana_instance=remote_kaapana_instance,
            action="external_update",
        )

        # create workflow for incoming workflow if does NOT exist yet
        for incoming_workflow in incoming_workflows:
            # check if incoming_workflow already exists
            db_incoming_workflow = get_workflow(
                db, workflow_id=incoming_workflow["workflow_id"]
            )
            # db_incoming_workflow = get_workflow(db, workflow_name=incoming_workflow['workflow_name']) # rather query via workflow_name than via workflow_id
            if db_incoming_workflow is None:
                # if not: create incoming workflows
                incoming_workflow["kaapana_instance_id"] = db_remote_kaapana_instance.id
                # incoming_workflow['external_workflow_id'] = incoming_workflow["id"]
                # convert string "{node81_gpu, node82_gpu}" to list ['node81_gpu', 'node82_gpu']
                incoming_workflow["involved_kaapana_instances"] = incoming_workflow[
                    "involved_kaapana_instances"
                ][1:-1].split(",")
                # Todo why is incoming_workflow such a strange object?
                # print('helllo', incoming_workflow[
                #     "involved_kaapana_instances"
                # ])
                # incoming_workflow["involved_kaapana_instances"] = json.dumps(incoming_workflow[
                #     "involved_kaapana_instances"
                # ])
                workflow = schemas.WorkflowCreate(**incoming_workflow)
                db_workflow = create_workflow(db, workflow)
                logging.debug(f"Created incoming remote workflow: {db_workflow}")

        # create incoming jobs
        fernet = Fernet(db_client_kaapana.encryption_key)
        db_jobs = []
        for incoming_job in incoming_jobs:
            if (
                "conf_data" in incoming_job
                and "data_form" in incoming_job["conf_data"]
                and "identifiers" in incoming_job["conf_data"]["data_form"]
            ):
                incoming_job["conf_data"]["data_form"]["identifiers"] = [
                    fernet.decrypt(identifier.encode()).decode()
                    for identifier in incoming_job["conf_data"]["data_form"][
                        "identifiers"
                    ]
                ]

            incoming_job["kaapana_instance_id"] = db_client_kaapana.id
            incoming_job[
                "owner_kaapana_instance_name"
            ] = db_remote_kaapana_instance.instance_name
            incoming_job["external_job_id"] = incoming_job["id"]
            incoming_job["status"] = "pending"
            job = schemas.JobCreate(**incoming_job)
            job.automatic_execution = (
                db_incoming_workflow.automatic_execution
                if db_incoming_workflow is not None
                else db_workflow.automatic_execution
            )
            db_job = create_job(db, job)
            db_jobs.append(db_job)

        # update incoming workflows
        for incoming_workflow in incoming_workflows:
            workflow_update = schemas.WorkflowUpdate(
                **{
                    "workflow_id": incoming_workflow["workflow_id"],
                    # incoming_workflow["workflow_name"] instead of db_incoming_workflow.workflow_name
                    "workflow_name": incoming_workflow["workflow_name"],
                    # db_jobs instead of incoming_jobs
                    "workflow_jobs": db_jobs,
                }
            )
            db_workflow = put_workflow_jobs(db, workflow_update)
            logging.debug(f"Updated remote workflow: {db_workflow}")

    return  # schemas.RemoteKaapanaInstanceUpdateExternal(**udpate_instance_payload)


def sync_states_from_airflow(db: Session, status: str = None, periodically=False):
    # get list from airflow for jobs in status=status: {'dag_run_id': 'state'} -> airflow_jobs_in_qsr_state
    airflow_jobs_in_state = get_dagruns_airflow(tuple([status]))
    # get list from db with all db_jobs in status=status
    db_jobs_in_state = get_jobs(db, status=status)

    # find elements which are in current airflow_jobs_runids but not in db_jobs_runids from previous round
    diff_airflow_to_db = [
        job
        for job in airflow_jobs_in_state
        if job["run_id"] not in [db_job.run_id for db_job in db_jobs_in_state]
    ]
    # find elements which are in db_jobs_runids from previous round but not in current airflow_jobs_runids
    diff_db_to_airflow = [
        db_job
        for db_job in db_jobs_in_state
        if db_job.run_id not in [job["run_id"] for job in airflow_jobs_in_state]
    ]

    if len(diff_airflow_to_db) > 0:
        # request airflow for states of all jobs in diff_airflow_to_db && update db_jobs of all jobs in diff_airflow_to_db
        for diff_job_af in diff_airflow_to_db:
            # get db_job from db via 'run_id' (fails for all airflow jobs which aren't user-created aka service-jobs)
            db_job = get_job(db, run_id=diff_job_af["run_id"])
            if db_job is not None:
                # update db_job w/ updated state
                job_update = schemas.JobUpdate(
                    **{
                        "job_id": db_job.id,
                    }
                )
                update_job(db, job_update, remote=False)
            else:
                # should only go into this condition for service-job
                create_and_update_service_workflows_and_jobs(
                    db,
                    diff_job_dagid=diff_job_af["dag_id"],
                    diff_job_runid=diff_job_af["run_id"],
                    status=status,
                )
    elif len(diff_db_to_airflow) > 0:
        # request airflow for states of all jobs in diff_db_to_airflow && update db_jobs of all jobs in diff_db_to_airflow
        for diff_db_job in diff_db_to_airflow:
            if diff_db_job.run_id is None:
                logging.debug(
                    "Remote db_job --> created to be executed on remote instance!"
                )
                continue
            # get db_job from db via 'run_id'
            db_job = get_job(db, run_id=diff_db_job.run_id)
            # get runner kaapana instance of db_job
            if db_job is not None:
                # update db_job w/ updated state
                job_update = schemas.JobUpdate(
                    **{
                        "job_id": db_job.id,
                    }
                )
                update_job(db, job_update, remote=False)
    elif len(diff_airflow_to_db) == 0 and len(diff_db_to_airflow) == 0:
        pass  # airflow and db in sync :)
    else:
        logging.error("Error while syncing kaapana-backend with Airflow")


def create_and_update_service_workflows_and_jobs(
    db: Session,
    diff_job_dagid: str = None,
    diff_job_runid: str = None,
    status: str = None,
):
    # get local kaapana instance
    db_local_kaapana_instance = get_kaapana_instance(db)

    # compose JobCreate object
    job = schemas.JobCreate(
        **{
            "status": status,
            "dag_id": diff_job_dagid,
            "run_id": diff_job_runid,
            "kaapana_instance_id": db_local_kaapana_instance.id,
            "owner_kaapana_instance_name": db_local_kaapana_instance.instance_name,
            "service_job": True,
            # service jobs should always be executed
            "automatic_execution": True,
            # further attributes for schemas.JobCreate
        }
    )
    # create service-job via crud.create_job() and JobCreate object
    db_job = create_job(db, job, service_job=True)

    # check whether service-workflow for that kind of service-job already exists
    db_service_workflow = get_workflow(db, dag_id=db_job.dag_id)
    if db_service_workflow:
        # if yes: compose WorkflowUpdate and append service-jobs to service-workflow via crud.put_workflow_jobs()
        workflow_update = schemas.WorkflowUpdate(
            **{
                "workflow_id": db_service_workflow.workflow_id,
                "workflow_name": f"{db_job.dag_id}-service-workflow",
                "workflow_jobs": [db_job],
            }
        )
        db_service_workflow = put_workflow_jobs(db, workflow_update)
        logging.debug(f"Updated service workflow: {db_service_workflow}")
    else:
        # if no: compose WorkflowCreate to create service-workflow ...
        workflow_create = schemas.WorkflowCreate(
            **{
                "workflow_id": f"ID-{''.join([substring[0] for substring in db_job.dag_id.split('-')])}",
                "workflow_name": f"{db_job.dag_id}-service-workflow",
                "kaapana_instance_id": db_local_kaapana_instance.id,
                "dag_id": db_job.dag_id,
                "service_workflow": True,
                "username": "system",
                # "username": request.headers["x-forwarded-preferred-username"],
            }
        )
        db_service_workflow = create_workflow(
            db=db, workflow=workflow_create, service_workflow=True
        )
        logging.debug(f"Created service workflow: {db_service_workflow}")
        # ... and afterwards append service-jobs to service-workflow via crud.put_workflow_jobs()
        workflow_update = schemas.WorkflowUpdate(
            **{
                "workflow_id": db_service_workflow.workflow_id,
                "workflow_name": db_service_workflow.workflow_name,
                "workflow_jobs": [db_job],
            }
        )
        db_service_workflow = put_workflow_jobs(db, workflow_update)
        logging.debug(f"Updated service workflow: {db_service_workflow}")


# def sync_states_from_airflow(db: Session, status: str = None, periodically=False):

#     # get list from airflow for jobs in states 'queued', 'scheduled', 'running': {'dag_run_id': 'state'} -> airflow_jobs_in_qsr_state
#     states = ["queued", "scheduled", "running"]
#     airflow_jobs_in_qsr_state = get_dagruns_airflow(tuple(states))
#     # extract list of run_ids of jobs in qsr states
#     airflow_jobs_qsr_runids = []
#     for airflow_job in airflow_jobs_in_qsr_state:
#         airflow_jobs_qsr_runids.append(airflow_job['run_id'])

#     # get list from db with all db_jobs in states 'queued', 'scheduled', 'running'
#     db_jobs_in_q_state = get_jobs(db, status="queued")
#     db_jobs_in_s_state = get_jobs(db, status="scheduled")
#     db_jobs_in_r_state = get_jobs(db, status="running")
#     db_jobs_in_qsr_state = db_jobs_in_q_state + db_jobs_in_s_state + db_jobs_in_r_state
#     # extract list of dag_run_ids from db_jobs_in_qsr_state
#     db_jobs_qsr_runids = []
#     for db_job in db_jobs_in_qsr_state:
#         db_jobs_qsr_runids.append(db_job.run_id)

#     # find elements which are in current airflow_jobs_in_qsr_state but not in db_jobs_in_qsr_state from previous round
#     diff_airflow_to_db = [elem for elem in airflow_jobs_qsr_runids if elem not in db_jobs_qsr_runids]
#     # find elements which are in db_jobs_in_qsr_state from previous round but not in current airflow_jobs_in_qsr_state
#     diff_db_to_airflow = [elem for elem in db_jobs_qsr_runids if elem not in airflow_jobs_qsr_runids]

#     if len(diff_airflow_to_db) > 0:
#         # request airflow for states of all jobs in diff_airflow_to_db && update db_jobs of all jobs in diff_airflow_to_db
#         for diff_job_runid in diff_airflow_to_db:
#             # get db_job from db via 'run_id'
#             db_job = get_job(db, run_id=diff_job_runid) # fails for all airflow jobs which aren't user-created aka service-jobs
#             if db_job is not None:
#                 # update db_job w/ updated state
#                 job_update = schemas.JobUpdate(**{
#                         'job_id': db_job.id,
#                         })
#                 update_job(db, job_update, remote=False)

#     elif len(diff_db_to_airflow) > 0:
#         # request airflow for states of all jobs in diff_db_to_airflow && update db_jobs of all jobs in diff_db_to_airflow
#         for diff_job_runid in diff_db_to_airflow:
#             if diff_job_runid is None:
#                 logging.info("Remote db_job --> created to be executed on remote instance!")
#                 pass
#             # get db_job from db via 'run_id'
#             db_job = get_job(db, run_id=diff_job_runid)
#             # get runner kaapana instance of db_job
#             if db_job is not None:
#                 # update db_job w/ updated state
#                 job_update = schemas.JobUpdate(**{
#                         'job_id': db_job.id,
#                         })
#                 update_job(db, job_update, remote=False)

#     elif len(diff_airflow_to_db) == 0 and len(diff_db_to_airflow) == 0:
#         pass    # airflow and db in sync :)

#     else:
#         logging.error("Error while syncing kaapana-backend with Airflow")


def sync_n_clean_qsr_jobs_with_airflow(db: Session, periodically=False):
    """
    Function to clean up unsuccessful synced jobs between airflow and backend.
    Function asks in backend for jobs in states 'queued', 'scheduled', 'running', asks Airflow for their real status and updates them.
    """
    # get db_jobs in states "queued", "scheduled", "running"
    db_jobs_queued = get_jobs(db, status="queued")
    db_jobs_scheduled = get_jobs(db, status="scheduled")
    db_jobs_running = get_jobs(db, status="running")
    db_jobs_qsr = db_jobs_queued + db_jobs_scheduled + db_jobs_running

    # iterate over db_jobs_qsr
    for db_job in db_jobs_qsr:
        # call crud.update job fpr each db_job in list to sync it's state from airflow
        job_update = schemas.JobUpdate(
            **{
                "job_id": db_job.id,
            }
        )
        update_job(db, job_update, remote=False)


def create_dataset(db: Session, dataset: schemas.DatasetCreate):
    logging.debug(f"Creating Dataset: {dataset.name}")

    if dataset.kaapana_instance_id is None:
        db_kaapana_instance = (
            db.query(models.KaapanaInstance).filter_by(remote=False).first()
        )
    else:
        db_kaapana_instance = (
            db.query(models.KaapanaInstance)
            .filter_by(id=dataset.kaapana_instance_id)
            .first()
        )

    if db.query(models.Dataset).filter_by(name=dataset.name).first():
        raise HTTPException(status_code=409, detail="Dataset already exists!")

    if not db_kaapana_instance:
        raise HTTPException(status_code=404, detail="Kaapana instance not found")

    utc_timestamp = get_utc_timestamp()

    db_dataset = models.Dataset(
        username=dataset.username,
        name=dataset.name,
        identifiers=json.dumps(dataset.identifiers),
        time_created=utc_timestamp,
        time_updated=utc_timestamp,
    )

    db_kaapana_instance.datasets.append(db_dataset)
    db.add(db_kaapana_instance)
    db.commit()
    logging.debug(f"Successfully created dataset: {dataset.name}")

    db.refresh(db_dataset)
    return db_dataset


def get_dataset(db: Session, name: str, raise_if_not_existing=True):
    db_dataset = db.query(models.Dataset).filter_by(name=name).first()
    if not db_dataset and raise_if_not_existing:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return db_dataset


def get_datasets(
    db: Session,
    instance_name: str = None,
    limit=None,
    username: str = None,
) -> List[models.Dataset]:
    logging.debug(username)
    # if username is not None:
    #     db_datasets = (
    #         db.query(models.Dataset)
    #         .filter_by(username=username)
    #         .join(models.Dataset.kaapana_instance, aliased=True)
    #         .order_by(desc(models.Dataset.time_updated))
    #         .limit(limit)
    #         .all()
    #     )
    # else:
    db_datasets = (
        db.query(models.Dataset)
        # .join(models.Dataset.kaapana_instance, aliased=True)
        .order_by(desc(models.Dataset.time_updated))
        .limit(limit)
        .all()
    )

    return db_datasets


def delete_dataset(db: Session, name: str):
    db_dataset = get_dataset(db, name)
    db.delete(db_dataset)
    db.commit()
    return {"ok": True}


def delete_datasets(db: Session):
    items = db.query(models.Dataset).all()
    [db.delete(item) for item in items]
    db.commit()
    return {"ok": True}


def update_dataset(db: Session, dataset=schemas.DatasetUpdate):
    logging.debug(f"Updating dataset {dataset.name}")
    db_dataset = get_dataset(db, dataset.name, raise_if_not_existing=False)

    if not db_dataset:
        logging.debug(f"Dataset {dataset.name} doesn't exist. Creating it.")
        db_dataset = create_dataset(
            db,
            DatasetCreate(name=dataset.name),
        )
        logging.debug(f"Dataset {dataset.name} created.")

    if dataset.action == "ADD":
        db_dataset.identifiers = json.dumps(
            list(set(dataset.identifiers + json.loads(db_dataset.identifiers)))
        )
    elif dataset.action == "DELETE":
        db_dataset.identifiers = json.dumps(
            [
                identifier
                for identifier in json.loads(db_dataset.identifiers)
                if identifier not in dataset.identifiers
            ]
        )
    elif dataset.action == "UPDATE":
        db_dataset.identifiers = json.dumps(dataset.identifiers)
    else:
        raise ValueError(f"Invalid action {dataset.action}")

    logging.debug(f"Successful updated Dataset {dataset.name}")
    # db_dataset.username = username
    db.commit()
    db.refresh(db_dataset)
    return db_dataset


def create_workflow(
    db: Session, workflow: schemas.WorkflowCreate, service_workflow: bool = False
):
    # workflow has a kaapana_instance_id?
    if workflow.kaapana_instance_id is None:
        # no: take first element on non-remote Kaapana instances in db
        db_kaapana_instance = (
            db.query(models.KaapanaInstance).filter_by(remote=False).first()
        )
    else:
        # yes: search Kaapana instance in db according to given kaapana_instance_id
        db_kaapana_instance = (
            db.query(models.KaapanaInstance)
            .filter_by(id=workflow.kaapana_instance_id)
            .first()
        )

    # get local kaapana instance
    db_local_kaapana_instance = get_kaapana_instance(db)

    # workflow already exists?
    if get_workflow(db, workflow_id=workflow.workflow_id) and service_workflow is False:
        raise HTTPException(
            status_code=409, detail="Workflow exists already!"
        )  # ... raise http exception!
    if not db_kaapana_instance:  # no kaapana_instance found in db in previous "search"?
        raise HTTPException(
            status_code=404, detail="Kaapana instance not found"
        )  # ... raise http exception!

    utc_timestamp = get_utc_timestamp()

    db_workflow = models.Workflow(
        workflow_id=workflow.workflow_id,
        kaapana_id=workflow.kaapana_instance_id,
        dag_id=workflow.dag_id,
        username=workflow.username,
        workflow_name=workflow.workflow_name,
        workflow_jobs=workflow.workflow_jobs,
        # list workflow_jobs already added to workflow in client.py's def create_workflow()
        involved_kaapana_instances=workflow.involved_kaapana_instances,
        service_workflow=workflow.service_workflow,
        time_created=utc_timestamp,
        time_updated=utc_timestamp,
        federated=workflow.federated,
    )
    if db_kaapana_instance.remote is False:
        # db_kaapana_instance.remote is False aka. db_kaapana_instance == db_local_kaapana_instance
        db_workflow.automatic_execution = True
    if db_kaapana_instance.remote is True:
        # give remote workflow always same automatic_execution permissions as local instance!
        db_workflow.automatic_execution = (
            db_local_kaapana_instance.automatic_workflow_execution
        )

    # TODO: also update all involved_kaapana_instances with the workflow_id in which they are involved

    db_kaapana_instance.workflows.append(db_workflow)
    db.add(db_kaapana_instance)
    db.commit()
    db.refresh(db_workflow)
    return db_workflow


# TODO removed async because our current database is not able to execute async methods
# async def queue_generate_jobs_and_add_to_workflow(
def queue_generate_jobs_and_add_to_workflow(
    db: Session,
    db_workflow: models.Workflow,
    json_schema_data: schemas.JsonSchemaData,
):
    conf_data = json_schema_data.conf_data
    # get variables
    single_execution = (
        "workflow_form" in conf_data
        and "single_execution" in conf_data["workflow_form"]
        and conf_data["workflow_form"]["single_execution"] is True
    )

    dataset_limit = (
        int(conf_data["data_form"]["dataset_limit"])
        if (
            "data_form" in conf_data
            and "dataset_limit" in conf_data["data_form"]
            and conf_data["data_form"]["dataset_limit"] is not None
        )
        else None
    )

    username = (
        conf_data["workflow_form"]["username"]
        if "username" in conf_data["workflow_form"]
        else json_schema_data.username
    )

    # if json_schema_data.federated:
    #     db_kaapana_instances = get_kaapana_instance(db, instance_name=)
    # else:
    db_kaapana_instances = get_kaapana_instances(
        db,
        filter_kaapana_instances=schemas.FilterKaapanaInstances(
            **{
                "instance_names": conf_data["workflow_form"]["runner_instances"]
                if not json_schema_data.federated
                else json_schema_data.instance_names,
            }
        ),
    )
    db_jobs = []
    for db_kaapana_instance in db_kaapana_instances:
        identifiers = []
        if "data_form" in conf_data and "dataset_name" in conf_data["data_form"]:
            dataset_name = conf_data["data_form"]["dataset_name"]
            if not db_kaapana_instance.remote:
                db_dataset = get_dataset(db, dataset_name)
                identifiers = json.loads(db_dataset.identifiers)
            else:
                allowed_datasets = json.loads(db_kaapana_instance.allowed_datasets)
                for dataset_info in allowed_datasets:
                    if dataset_info["name"] == dataset_name:
                        identifiers = (
                            dataset_info["identifiers"]
                            if "identifiers" in dataset_info
                            else []
                        )
                        break

            conf_data["data_form"].update({"identifiers": identifiers})

        # compose queued_jobs according to 'single_execution'
        queued_jobs = []
        if single_execution is True:
            for identifier in conf_data["data_form"]["identifiers"][:dataset_limit]:
                # Copying due to reference?!
                single_conf_data = copy.deepcopy(conf_data)
                single_conf_data["data_form"]["identifiers"] = [identifier]
                queued_jobs.append(
                    {
                        "conf_data": single_conf_data,
                        "dag_id": json_schema_data.dag_id,
                        "username": username,
                    }
                )
        else:
            # if identifiers:
            #     conf_data["data_form"].update({"identifiers": identifiers})
            queued_jobs = [
                {
                    "conf_data": conf_data,
                    "dag_id": json_schema_data.dag_id,
                    # 'dag_id': json_schema_data.dag_id if json_schema_data.federated == False else conf_data['external_schema_federated_form']['remote_dag_id'],
                    "username": username,
                }
            ]
        for jobs_to_create in queued_jobs:
            job = schemas.JobCreate(
                **{
                    "status": "queued",
                    "kaapana_instance_id": db_kaapana_instance.id,
                    "owner_kaapana_instance_name": settings.instance_name,
                    "automatic_execution": db_workflow.automatic_execution,
                    **jobs_to_create,
                }
            )
            db_job = create_job(db, job)
            db_jobs.append(db_job)

    # update workflow w/ created db_jobs
    workflow = schemas.WorkflowUpdate(
        **{
            "workflow_id": db_workflow.workflow_id,
            "workflow_name": db_workflow.workflow_name,
            "workflow_jobs": db_jobs,
        }
    )
    db_workflow = put_workflow_jobs(db, workflow)

    # would be better to solve this with a lamba function instead of putting it directly here
    # db.close()

    return {
        "workflow": db_workflow,
        "jobs": db_jobs,
    }


def get_workflow(
    db: Session, workflow_id: str = None, workflow_name: str = None, dag_id: str = None
):
    if workflow_id is not None:
        return db.query(models.Workflow).filter_by(workflow_id=workflow_id).first()
    elif workflow_name is not None:
        return db.query(models.Workflow).filter_by(workflow_name=workflow_name).first()
    elif dag_id is not None:
        return db.query(models.Workflow).filter_by(dag_id=dag_id).first()
    # if not db_workflow:
    #     raise HTTPException(status_code=404, detail="Workflow not found")
    # return db_workflow


def get_workflows(
    db: Session,
    instance_name: str = None,
    involved_instance_name: str = None,
    workflow_job_id: int = None,
    limit=None,
):
    if instance_name is not None:
        return (
            db.query(models.Workflow)
            .join(models.Workflow.kaapana_instance, aliased=True)
            .filter_by(instance_name=instance_name)
            .order_by(desc(models.Workflow.time_updated))
            .limit(limit)
            .all()
        )
    elif involved_instance_name is not None:
        return (
            db.query(models.Workflow)
            .filter(
                models.Workflow.involved_kaapana_instances.contains(
                    involved_instance_name
                )
            )
            .all()
        )
    elif workflow_job_id is not None:
        return (
            db.query(models.Workflow)
            .join(models.Workflow.workflow_jobs, aliased=True)
            .filter_by(id=workflow_job_id)
            .all()
        )
    else:
        return (
            db.query(models.Workflow)
            .join(models.Workflow.kaapana_instance)
            .order_by(desc(models.Workflow.time_updated))
            .limit(limit)
            .all()
        )  # , aliased=True


def update_workflow(db: Session, workflow=schemas.WorkflowUpdate):
    utc_timestamp = get_utc_timestamp()
    db_local_kaapana_instance = get_kaapana_instance(db)

    db_workflow = get_workflow(db, workflow.workflow_id)

    if db_workflow.federated and workflow.workflow_status != "abort":
        # federated workflow --> only restart orchestration job and not all jobs of workflow
        for workflow_job in db_workflow.workflow_jobs:
            if "external_schema_federated_form" in workflow_job.conf_data:
                restart_job_id = workflow_job.id
                break
        job = schemas.JobUpdate(
            **{
                "job_id": restart_job_id,
                "status": "scheduled",
            }
        )
        update_job(db, job, remote=False)
        return db_workflow

    if workflow.workflow_status == "confirmed":
        workflow.workflow_status = "confirmed"
        db_workflow.automatic_execution = True

    if workflow.workflow_status != "abort":  # usually 'scheduled' or 'confirmed'
        # iterate over db_jobs in db_workflow ...
        for db_workflow_current_job in db_workflow.workflow_jobs:
            # either update db_jobs on own kaapana_instance
            if (
                db_workflow.kaapana_instance.remote is False
                or (
                    db_workflow.kaapana_instance.remote is True
                    and db_workflow.kaapana_instance.automatic_workflow_execution
                    is True
                )
                or (
                    db_workflow.kaapana_instance.remote is True
                    and db_workflow.automatic_execution is True
                )
            ):
                job = schemas.JobUpdate(
                    **{
                        "job_id": db_workflow_current_job.id,
                        "status": "scheduled",
                        "description": "The worklow was triggered!",
                    }
                )
                # def update_job() expects job of class schemas.JobUpdate
                update_job(db, job, remote=False)
            # or update db_jobs on remote kaapana_instance
            elif (
                db_workflow.kaapana_instance.remote is True
                and db_workflow.kaapana_instance.automatic_workflow_execution is True
            ) or (
                db_workflow.kaapana_instance.remote is True
                and db_workflow.automatic_execution is True
            ):
                # def update_external_job expects db_workflow_current_job of class models.Job
                update_external_job(db, db_workflow_current_job)

            else:
                raise HTTPException(
                    status_code=404,
                    detail="Job updating while updating the workflow failed!",
                )

        # do call to remote's experiment to start jobs there
        # extract all remote involved_instances of workflow
        involved_instances = db_workflow.involved_kaapana_instances.strip("{}").split(
            ","
        )
        remote_involved_instances = [
            el
            for el in involved_instances
            if el != db_workflow.kaapana_instance.instance_name
        ]
        if (
            remote_involved_instances
            and db_workflow.kaapana_instance.instance_name
            == db_local_kaapana_instance.instance_name
        ):
            update_remote_workflow(db, db_workflow, remote_involved_instances)

    db_workflow.time_updated = utc_timestamp
    db.commit()
    db.refresh(db_workflow)

    return db_workflow


def update_remote_workflow(
    db: Session, db_workflow=models.Workflow, remote_involved_instances: List = []
):
    for remote_involved_instance in remote_involved_instances:
        # get remote_involved_instance
        db_remote_kaapana_instance = get_kaapana_instance(
            db, instance_name=remote_involved_instance
        )
        # compose payload
        payload = {
            "workflow_id": db_workflow.workflow_id,
            "workflow_status": "scheduled",
        }
        # call rmeote's update_worklfow endpoint
        remote_backend_url = f"{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/kaapana-backend/remote"
        with requests.Session() as s:
            r = requests_retry_session(session=s).put(
                f"{remote_backend_url}/workflow",
                verify=db_remote_kaapana_instance.ssl_check,
                json=payload,
                headers={
                    "FederatedAuthorization": f"{db_remote_kaapana_instance.token}"
                },
                timeout=TIMEOUT,
            )
        if r.status_code == 404:
            logging.warning(
                f"Workflow {db_workflow.workflow_id} does not exist on remote instance"
            )
        elif r.status_code != 200:
            logging.error("Error in CRUD def update_remote_workflow()")
            raise_kaapana_connection_error(r)
            logging.error(r.json())


def put_workflow_jobs(db: Session, workflow=schemas.WorkflowUpdate):
    utc_timestamp = get_utc_timestamp()

    # db_workflow = get_workflow(db, workflow_name=workflow.workflow_name)
    db_workflow = get_workflow(db, workflow_id=workflow.workflow_id)

    # get db_jobs via job_id which should be added to db_workflow
    db_jobs = []
    for workflow_job in workflow.workflow_jobs:
        if type(workflow_job) is dict:
            # workflow_job is a dict when call of def put_workflow_jobs() comes from backend
            db_job = get_job(db, workflow_job["id"])
        else:
            # workflow_job is no dict when call of def put_workflow_jobs() comes from KaapanaFederatedTraining
            db_job = get_job(db, workflow_job.id)
        db_jobs.append(db_job)

    # add dat shit to dat workflow
    db_workflow.workflow_jobs.extend(db_jobs)
    # TODO: create set of db_workflow.workflow_jobs to avoid double listed jobs

    db_workflow.time_updated = utc_timestamp
    db.commit()
    db.refresh(db_workflow)

    return db_workflow


def delete_workflow(db: Session, workflow_id: str):
    # get db's db_workflow object
    db_workflow = get_workflow(db, workflow_id)

    # iterate over jobs of to-be-deleted workflow
    for db_workflow_current_job in db_workflow.workflow_jobs:
        delete_job(
            db, job_id=db_workflow_current_job.id, remote=False
        )  # deletes local and remote jobs

    db.delete(db_workflow)
    db.commit()
    return {"ok": True}


def delete_workflows(db: Session):
    # TODO: add remote workflow deletion
    db.query(models.Workflow).delete()
    db.commit()
    return {"ok": True}
