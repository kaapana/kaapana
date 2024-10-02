import json
import os
import logging
import uuid
import copy
from typing import List
import datetime
import string
import requests
from threading import Thread
import traceback
from cryptography.fernet import Fernet
from fastapi import HTTPException, Response
from psycopg2.errors import UniqueViolation
from sqlalchemy import desc, delete
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, String, JSON
from urllib3.util import Timeout
from app.config import settings
from app.database import SessionLocal
from . import models, schemas
from .schemas import DatasetCreate
from .utils import (
    generate_run_id,
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
    # os_processor,
)
from app.datasets.utils import get_meta_data


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
                cast(models.KaapanaInstance.allowed_dags, String).contains(
                    filter_kaapana_instances.dag_id
                )
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
                cast(models.KaapanaInstance.allowed_dags, String).contains(
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


def update_allowed_datasets_and_workflows(db: Session):
    available_dags = get_dag_list(kind_of_dags="viewNames:remoteExecution")
    available_datasets = [
        db_dataset.name for db_dataset in db.query(models.Dataset).all()
    ]
    db_kaapana_instance = get_kaapana_instance(db)
    update_needed = False
    allowed_dags = []
    for dag in db_kaapana_instance.allowed_dags:
        if dag in available_dags:
            allowed_dags.append(dag)
        else:
            update_needed = True

    allowed_datasets = []
    for dataset in db_kaapana_instance.allowed_datasets:
        if dataset["name"] in available_datasets:
            allowed_datasets.append(dataset["name"])
        else:
            update_needed = True

    if update_needed:
        logging.debug("Updating allowed datasets and dags")
        logging.debug("Allowed datasets: " + str(allowed_datasets))
        logging.debug("Allowed dags: " + str(allowed_dags))
        instance_update = schemas.ClientKaapanaInstanceCreate(
            ssl_check=db_kaapana_instance.ssl_check,
            automatic_update=db_kaapana_instance.automatic_update,
            automatic_workflow_execution=db_kaapana_instance.automatic_workflow_execution,
            fernet_encrypted=db_kaapana_instance.fernet_key != "deactivated",
            allowed_dags=allowed_dags,
            allowed_datasets=allowed_datasets,
        )
        create_and_update_client_kaapana_instance(db, instance_update, action="update")
    else:
        logging.debug("No update needed")


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
            remote=False,
            time_created=utc_timestamp,
            time_updated=utc_timestamp,
            client_time_update=utc_timestamp,
            automatic_update=client_kaapana_instance.automatic_update or False,
            automatic_workflow_execution=client_kaapana_instance.automatic_workflow_execution
            or False,
        )
    elif action == "update":
        allowed_dags = get_dag_list(
            only_dag_names=False,
            filter_allowed_dags=client_kaapana_instance.allowed_dags,
        )

        allowed_datasets = []
        for dataset_name in client_kaapana_instance.allowed_datasets:
            db_dataset = get_dataset(db, name=dataset_name, raise_if_not_existing=False)
            if db_dataset:
                identifiers = [identifier.id for identifier in db_dataset.identifiers]
                dataset = schemas.AllowedDatasetCreate(
                    name=db_dataset.name,
                    username=db_dataset.username,
                    identifiers=identifiers,
                ).model_dump()

                meta_information = {}
                # Todo add here unique studies and patients to the db_dataset object!
                meta_data = get_meta_data(
                    identifiers,
                    drop_duplicate_studies=False,
                    drop_duplicated_patients=False,
                )
                dataset["identifiers_count"] = len(meta_data)
                meta_information.update(
                    {
                        "identifiers": {
                            "identifiers": list(meta_data.keys()),
                            "meta_data": meta_data,
                        }
                    }
                )
                meta_data = get_meta_data(
                    identifiers,
                    drop_duplicate_studies=True,
                    drop_duplicated_patients=False,
                )
                dataset["series_uids_with_unique_study_uids_count"] = len(meta_data)
                meta_information.update(
                    {
                        "series_uids_with_unique_study_uids_count": {
                            "identifiers": list(meta_data.keys()),
                            "meta_data": meta_data,
                        }
                    }
                )
                meta_data = get_meta_data(
                    identifiers,
                    drop_duplicate_studies=False,
                    drop_duplicated_patients=True,
                )
                dataset["series_ids_with_unique_patient_ids_count"] = len(meta_data)
                meta_information.update(
                    {
                        "series_ids_with_unique_patient_ids_count": {
                            "identifiers": list(meta_data.keys()),
                            "meta_data": meta_data,
                        }
                    }
                )
                db_dataset.meta_information = meta_information

                db.commit()
                db.refresh(db_dataset)
                allowed_datasets.append(dataset)

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
        db_client_kaapana_instance.remote_update_log = (
            client_kaapana_instance.remote_update_log
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
    client_update=False,
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
        if "" in [
            remote_kaapana_instance.host,
            remote_kaapana_instance.instance_name,
            remote_kaapana_instance.token,
        ]:
            raise HTTPException(
                status_code=400, detail="Instance name, Host and Token must be defined!"
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
            time_updated=datetime.datetime.min,
            client_time_update=datetime.datetime.min,
        )
    elif action == "update":
        db_remote_kaapana_instance.token = remote_kaapana_instance.token
        db_remote_kaapana_instance.port = remote_kaapana_instance.port
        db_remote_kaapana_instance.ssl_check = remote_kaapana_instance.ssl_check
        db_remote_kaapana_instance.fernet_key = (
            remote_kaapana_instance.fernet_key or "deactivated"
        )
    elif action == "external_update":
        logging.debug(
            f"Externally updating with db_remote_kaapana_instance: {db_remote_kaapana_instance}"
        )
        if db_remote_kaapana_instance:
            db_remote_kaapana_instance.allowed_dags = (
                remote_kaapana_instance.allowed_dags
            )
            db_remote_kaapana_instance.allowed_datasets = (
                remote_kaapana_instance.allowed_datasets
            )
            db_remote_kaapana_instance.automatic_update = (
                remote_kaapana_instance.automatic_update or False
            )
            db_remote_kaapana_instance.automatic_workflow_execution = (
                remote_kaapana_instance.automatic_workflow_execution or False
            )
            if client_update:
                db_remote_kaapana_instance.client_time_update = utc_timestamp
            else:
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
        minioClient = HelperMinio()
        minio_urls = minioClient.add_minio_urls(
            job.conf_data["federated_form"], db_kaapana_instance.instance_name
        )
        job.conf_data["federated_form"]["minio_urls"] = minio_urls

    utc_timestamp = get_utc_timestamp()

    db_job = models.Job(
        # id = job.id,    # not sure if this shouldn't be set automatically
        conf_data=job.conf_data,
        time_created=utc_timestamp,
        time_updated=utc_timestamp,
        external_job_id=job.external_job_id,
        username=job.username,
        dag_id=job.dag_id,
        # run_id only for service-jobs which are already running in airflow w/known run_id before corresponding db_job is created
        run_id=job.run_id if job.run_id else generate_run_id(job.dag_id),
        kaapana_id=job.kaapana_instance_id,
        owner_kaapana_instance_name=job.owner_kaapana_instance_name,
        # replaced addressed_kaapana_instance_name w/ owner_kaapana_instance_name or None
        update_external=True if job.external_job_id else job.update_external,
        status=job.status,
        automatic_execution=job.automatic_execution,
        service_job=job.service_job,
    )

    db.add(db_job)

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
        bulk_update_jobs(db, [job])

    return db_job


def get_job(db: Session, job_id: int = None, run_id: str = None):
    if job_id is not None:
        db_job = db.query(models.Job).filter_by(id=job_id).first()
    elif run_id is not None:
        db_job = db.query(models.Job).filter_by(run_id=run_id).first()
    if not db_job:
        logging.error(
            f"No job found in db with job_id={job_id}, run_id={run_id} --> will return None"
        )
        raise HTTPException(status_code=404, detail="Job not found")

    return db_job


def delete_job(db: Session, job_id: int):
    db_job = get_job(db, job_id)
    if db_job.status in ["queued", "scheduled", "running"]:
        raise HTTPException(
            status_code=401,
            detail="You are not allowed to delete this job, since its not in queued, scheduled or running state",
        )

    if db_job.update_external:
        raise HTTPException(
            status_code=202,
            detail="Job is currently updating, please try again, once the update finished.",
        )

    job = schemas.JobUpdate(
        **{
            "job_id": db_job.id,
            "status": "deleted",
            "update_external": db_job.runs_on_remote,
        }
    )
    bulk_update_jobs(db, [job])
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
    dag_id: str = None,
    username: str = None,
):
    query = db.query(models.Job)
    if dag_id is not None:
        query = query.filter_by(dag_id=dag_id)
    if username is not None:
        query = query.filter_by(username=username)

    # The rest could be cleaned up someday, but it needs to be assessed what really needs to be returned depending on the if conditions...
    if instance_name is not None and status is not None:
        return (
            query.filter_by(status=status)
            .join(models.Job.kaapana_instance, aliased=True)
            .filter_by(instance_name=instance_name)
            .order_by(desc(models.Job.time_updated))
            .limit(limit)
            .all()
        )  # same as org but w/o filtering by remote
    elif workflow_name is not None and status is not None:
        return (
            query.filter_by(status=status)
            .join(models.Job.workflow, aliased=True)
            .filter_by(workflow_name=workflow_name)
            .order_by(desc(models.Job.time_updated))
            .limit(limit)
            .all()
        )
    elif instance_name is not None:
        return (
            query.join(models.Job.kaapana_instance, aliased=True)
            .filter_by(instance_name=instance_name)
            .order_by(desc(models.Job.time_updated))
            .limit(limit)
            .all()
        )  # same as org but w/o filtering by remote
    elif workflow_name is not None:
        return (
            query.join(models.Job.workflow, aliased=True)
            .filter_by(workflow_name=workflow_name)
            .order_by(desc(models.Job.time_updated))
            .limit(limit)
            .all()
        )
    elif status is not None:
        return (
            query.filter_by(status=status)
            .join(models.Job.kaapana_instance, aliased=True)
            .order_by(desc(models.Job.time_updated))
            .limit(limit)
            .all()
        )  # same as org but w/o filtering by remote
    else:
        return (
            query.join(models.Job.workflow, aliased=True)
            .join(models.Workflow.kaapana_instance, aliased=True)
            .filter_by(remote=remote)
            .order_by(desc(models.Job.time_updated))
            .limit(limit)
            .all()
        )
        # explanation: db.query(models.Job) returns a Query object; .join() creates more narrow Query objects ; filter_by() applies the filter criterion to the remaining Query (source: https://docs.sqlalchemy.org/en/14/orm/query.html#sqlalchemy.orm.Query)


def prepare_job_update(db_job, job):
    utc_timestamp = get_utc_timestamp()
    # update remote jobs in local db (def update_job() called from remote.py's def put_job() with remote=True)
    # if db_job.kaapana_instance.remote and remote:
    #     db_job.status = job.status

    if db_job.external_job_id is not None:
        db_job.update_external = True
    elif job.status == "deleted" and db_job.status == "created":
        db_job.update_external = False
    else:
        db_job.update_external = job.update_external

    if job.status == "restart":
        db_job.run_id = generate_run_id(db_job.dag_id)
        db_job.status = "scheduled"
    elif job.status == "deleted" and db_job.status not in [
        "created",
        "pending",
        "finished",
        "deleted",
        "failed",
        "aborted",
    ]:
        logging.error(
            f"Job with job_id {job.job_id} cannot be deleted, since it is in state {db_job.status}"
        )
    else:
        db_job.status = job.status

    if db_job.status == "scheduled" and db_job.kaapana_instance.remote == False:
        # or (job.status == 'failed'); status='scheduled' for restarting, status='failed' for aborting
        conf_data = db_job.conf_data
        conf_data["client_job_id"] = db_job.id
        dag_id_and_dataset = check_dag_id_and_dataset(
            db_job.kaapana_instance,
            conf_data,
            db_job.dag_id,
            db_job.owner_kaapana_instance_name,
        )
        if dag_id_and_dataset is not None:
            db_job.status = "failed"
            db_job.description = dag_id_and_dataset

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
    return db_job


def bulk_delete_jobs(db: Session, job_ids_to_delete: List[int]):
    delete_query = delete(models.Job).where(models.Job.id.in_(job_ids_to_delete))
    db.execute(delete_query)
    db.commit()
    return {"ok": True}


def bulk_update_jobs(db: Session, jobs: List[schemas.JobUpdate]):
    job_ids = [job.job_id for job in jobs]

    db_jobs = db.query(models.Job).filter(models.Job.id.in_(job_ids)).all()
    job_map = {job.id: job for job in db_jobs}
    lost_job_ids = []
    updated_db_jobs = []
    for job in jobs:
        db_job = job_map.get(job.job_id)
        if db_job:
            db_job = prepare_job_update(db_job, job)
            updated_db_jobs.append(db_job)
        else:
            logging.error(f"Job with job_id {job.job_id} not found in db")
            lost_job_ids.append(job.job_id)
    # Bulk save objects
    if updated_db_jobs:
        db.bulk_save_objects(updated_db_jobs)
        db.commit()

    abort_db_jobs = []
    job_ids_to_delete = []
    for db_job in updated_db_jobs:
        if db_job.status == "scheduled" and db_job.kaapana_instance.remote == False:
            try:
                execute_job_airflow(db_job)
            except Exception as e:
                print(f"Failed to execute job {db_job.id}")
                job = schemas.JobUpdate(
                    **{
                        "job_id": db_job.id,
                        "status": "failed",
                        "description": "Failed to execute job",
                    }
                )
                bulk_update_jobs(db, [job])
        if db_job.status == "aborted":
            abort_db_jobs.append(db_job)
        if db_job.status == "deleted" and not db_job.update_external:
            job_ids_to_delete.append(db_job.id)

    if abort_db_jobs:
        try:
            abort_jobs_in_chunks(abort_db_jobs)
        except Exception as e:
            logging.error(f"Failed to abort jobs: {str(e)}")

    if job_ids_to_delete:
        try:
            bulk_delete_jobs(db, job_ids_to_delete)
        except Exception as e:
            logging.error(f"Failed to delete jobs: {str(e)}")

    return updated_db_jobs, lost_job_ids


def abort_jobs_in_chunks(db_jobs_to_abort):
    run_ids = []
    job_updates = []
    for db_job in db_jobs_to_abort:
        if db_job.runs_on_remote:  # Remote running job
            logging.debug(
                f"Skipping job {db_job.id}, since it is not running on the client site"
            )
        else:
            run_ids.append(db_job.run_id)
        job_updates.append(
            schemas.JobUpdate(
                **{
                    "job_id": db_job.id,
                    "status": "aborted",
                    "description": "Job was aborted!",
                }
            )
        )
    logging.debug("run_Ids: " + str(run_ids))
    if run_ids:
        try:
            abort_job_airflow(run_ids)
        except Exception as e:
            logging.error(f"Failed to abort jobs: {str(e)}")
            return {"error": str(e)}


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
    client_to_remote_instance: schemas.RemoteKaapanaInstanceUpdateExternal,
    client_to_remote_jobs: List[schemas.JobUpdate] = None,
):
    """
    Function call recevied at remote instance to sync client and remote
    """
    db_client_kaapana = get_kaapana_instance(db)

    # Local update of Kaapana Instance is happening in here...
    create_and_update_remote_kaapana_instance(
        db=db,
        remote_kaapana_instance=client_to_remote_instance,
        action="external_update",
        client_update=True,
    )

    # Handling incoming job updates
    if client_to_remote_jobs is not None:
        for job in client_to_remote_jobs:
            logging.debug(job)
        updated_client_to_remote_job, lost_client_to_remote_job_ids = bulk_update_jobs(
            db, client_to_remote_jobs
        )
    else:
        updated_client_to_remote_job = []
    # Also adding jobs that were not found here to the list, so that the remote system will not try to update them again
    updated_client_to_remote_job_ids = [job.id for job in updated_client_to_remote_job]
    logging.debug(
        f"SYNC_CLIENT_REMOTE updated_client_to_remote_job_ids: {updated_client_to_remote_job_ids}"
    )
    logging.debug(f"SYNC_CLIENT_REMOTE lost_job_ids: {lost_client_to_remote_job_ids}")

    # Preparing outgoing jobs and workflows
    db_remote_to_client_jobs = (
        db.query(models.Job)
        .join(models.Job.kaapana_instance)
        .filter(
            models.KaapanaInstance.instance_name
            == client_to_remote_instance.instance_name,
            models.Job.update_external == True,
            models.Job.kaapana_id != db_client_kaapana.id,  # Exclude local jobs
        )
        .all()
    )

    # Get workflows on client_kaapana_instance which contain outgoing jobs
    remote_to_client_workflow_ids = set(
        [job.workflow_id for job in db_remote_to_client_jobs]
    )

    # get workflows on client_kaapana_instance which contain remote_to_client_jobs
    remote_to_client_jobs = []
    for db_remote_to_client_job in db_remote_to_client_jobs:
        logging.debug(
            f"Job: {schemas.JobWithWorkflowId(**db_remote_to_client_job.__dict__).dict()}"
        )
        remote_to_client_jobs.append(
            schemas.JobWithWorkflowId(**db_remote_to_client_job.__dict__).dict()
        )

    remote_to_client_workflows = []
    for workflow_id in remote_to_client_workflow_ids:
        db_workflow = get_workflow(db, workflow_id=workflow_id)
        remote_to_client_workflows.append(
            schemas.Workflow(**db_workflow.__dict__).dict()
        )

    logging.debug(f"SYNC_CLIENT_REMOTE remote_to_client_jobs: {remote_to_client_jobs}")
    logging.debug(
        f"SYNC_CLIENT_REMOTE remote_to_client_workflows: {remote_to_client_workflows}"
    )

    # Instance specific update
    remote_to_client_instance = {
        "instance_name": db_client_kaapana.instance_name,
        "allowed_dags": db_client_kaapana.allowed_dags,
        "allowed_datasets": db_client_kaapana.allowed_datasets,
        "automatic_update": db_client_kaapana.automatic_update,
        "automatic_workflow_execution": db_client_kaapana.automatic_workflow_execution,
    }

    return {
        "updated_client_to_remote_job_ids": updated_client_to_remote_job_ids,
        "lost_client_to_remote_job_ids": lost_client_to_remote_job_ids,
        "remote_to_client_jobs": remote_to_client_jobs,
        "remote_to_client_workflows": remote_to_client_workflows,
        "remote_to_client_instance": remote_to_client_instance,
    }


def get_remote_updates(db: Session, periodically=False):
    """
    Function call recevied at client instance to sync client and remote
    """
    db_client_kaapana = get_kaapana_instance(db)
    try:
        if periodically is True and db_client_kaapana.automatic_update is False:
            logging.info("No automatic checking of remote instances enabled")
            return
        else:
            logging.info("Checking for remote updates")
        db_kaapana_instances = get_kaapana_instances(db)
        for db_remote_kaapana_instance in db_kaapana_instances:
            if not db_remote_kaapana_instance.remote:
                # Skipping locally running jobs
                continue

            # Preparing outgoing jobs and workflows
            db_client_to_remote_jobs = (
                db.query(
                    models.Job.owner_kaapana_instance_name,
                    models.Job.update_external,
                    models.Job.external_job_id,
                    models.Job.run_id,
                    models.Job.status,
                    models.Job.description,
                )
                .filter(
                    models.Job.owner_kaapana_instance_name
                    == db_remote_kaapana_instance.instance_name,
                    models.Job.update_external == True,
                )
                .all()
            )

            client_to_remote_jobs = []
            for db_client_to_remote_job in db_client_to_remote_jobs:
                job = {
                    "job_id": db_client_to_remote_job.external_job_id,
                    "run_id": db_client_to_remote_job.run_id,
                    "status": db_client_to_remote_job.status,
                    "description": db_client_to_remote_job.description,
                    "update_external": False,
                }
                client_to_remote_jobs.append(job)
            logging.info(
                f"GET_REMOTE_UPDATES Number of client_to_remote_jobs: {len(client_to_remote_jobs)}"
            )
            logging.debug(
                f"GET_REMOTE_UPDATES client_to_remote_jobs: {client_to_remote_jobs}"
            )

            # Instance specific update
            client_to_remote_instance = {
                "instance_name": db_client_kaapana.instance_name,
                "allowed_dags": db_client_kaapana.allowed_dags,
                "allowed_datasets": db_client_kaapana.allowed_datasets,
                "automatic_update": db_client_kaapana.automatic_update,
                "automatic_workflow_execution": db_client_kaapana.automatic_workflow_execution,
            }

            remote_backend_url = f"{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/kaapana-remote/remote"
            with requests.Session() as s:
                r = requests_retry_session(session=s, retries=1).put(
                    f"{remote_backend_url}/sync-client-remote",
                    json={
                        "client_to_remote_instance": client_to_remote_instance,
                        "client_to_remote_jobs": client_to_remote_jobs,
                    },
                    verify=db_remote_kaapana_instance.ssl_check,
                    headers={
                        "FederatedAuthorization": f"{db_remote_kaapana_instance.token}",
                        "User-Agent": f"kaapana",
                    },
                    timeout=TIMEOUT,
                )
            if r.status_code != 200:
                raise Exception(
                    f"We could not reach the following backend {db_remote_kaapana_instance.host} with status code {r.status_code} and error message {r.text}"
                )
            raise_kaapana_connection_error(r)
            remote_response = r.json()

            # Handling updated_job_ids
            updated_client_to_remote_job_ids = remote_response[
                "updated_client_to_remote_job_ids"
            ]
            db_jobs = (
                db.query(models.Job)
                .filter(
                    models.Job.external_job_id.in_(updated_client_to_remote_job_ids)
                )
                .all()
            )
            updated_db_jobs = []
            job_ids_to_delete = []
            for db_job in db_jobs:
                if db_job.status == "deleted":
                    job_ids_to_delete.append(db_job.id)
                db_job.update_external = False
                updated_db_jobs.append(db_job)
            # Bulk save objects
            db.bulk_save_objects(updated_db_jobs)
            db.commit()

            # Handling jobs that exist on the local instance but not on the remote instance
            lost_client_to_remote_job_ids = remote_response[
                "lost_client_to_remote_job_ids"
            ]
            db_jobs = (
                db.query(models.Job)
                .filter(models.Job.external_job_id.in_(lost_client_to_remote_job_ids))
                .all()
            )
            for db_job in db_jobs:
                if db_job.status == "deleted":
                    job_ids_to_delete.append(db_job.id)
                else:
                    logging.error(
                        f"Job with job_id {db_job.id} does not exist on remote system and will therefore be deleted."
                    )
                    job_ids_to_delete.append(db_job.id)

            if job_ids_to_delete:
                try:
                    bulk_delete_jobs(db, job_ids_to_delete)
                except Exception as e:
                    logging.error(f"Failed to delete jobs: {str(e)}")

            # Handling incoming jobs and workflows
            remote_to_client_jobs = remote_response["remote_to_client_jobs"]
            remote_to_client_workflows = remote_response["remote_to_client_workflows"]
            remote_kaapana_instance = schemas.RemoteKaapanaInstanceUpdateExternal(
                **remote_response["remote_to_client_instance"]
            )

            create_and_update_remote_kaapana_instance(
                db=db,
                remote_kaapana_instance=remote_kaapana_instance,
                action="external_update",
                client_update=False,
            )

            # create workflow for incoming workflow if does NOT exist yet
            db_workflow_dict = {}
            db_workflow_job_dict = {}
            for remote_to_client_workflow in remote_to_client_workflows:
                # check if remote_to_client_workflow already exists
                db_workflow = get_workflow(
                    db, workflow_id=remote_to_client_workflow["workflow_id"]
                )
                if db_workflow is None:
                    remote_to_client_workflow["kaapana_instance_id"] = (
                        db_remote_kaapana_instance.id
                    )
                    remote_to_client_workflow["involved_kaapana_instances"] = (
                        remote_to_client_workflow["involved_kaapana_instances"][
                            1:-1
                        ].split(",")
                    )
                    workflow = schemas.WorkflowCreate(**remote_to_client_workflow)
                    db_workflow = create_workflow(db, workflow)
                    logging.debug(f"Created incoming remote workflow: {db_workflow}")
                db_workflow_dict[db_workflow.workflow_id] = db_workflow
                db_workflow_job_dict[db_workflow.workflow_id] = []

            # Handling incoming jobs
            logging.info(
                f"GET_REMOTE_UPDATES Number of remote_to_client_jobs: {len(remote_to_client_jobs)}"
            )
            logging.debug(
                f"GET_REMOTE_UPDATES remote_to_client_jobs: {remote_to_client_jobs}"
            )
            db_remote_to_client_jobs = (
                db.query(
                    models.Job.id,
                    models.Job.external_job_id,
                )
                .filter(
                    models.Job.external_job_id.in_(
                        [job["id"] for job in remote_to_client_jobs]
                    )
                )
                .all()
            )
            incoming_external_job_ids = {
                job.external_job_id: job.id for job in db_remote_to_client_jobs
            }
            inncoming_update_jobs = []
            for remote_to_client_job in remote_to_client_jobs:
                if remote_to_client_job["id"] in incoming_external_job_ids:
                    remote_to_client_job["job_id"] = incoming_external_job_ids[
                        remote_to_client_job["id"]
                    ]
                    inncoming_update_jobs.append(
                        schemas.JobUpdate(**remote_to_client_job)
                    )
                else:
                    db_job = (
                        db.query(models.Job)
                        .filter_by(run_id=remote_to_client_job["run_id"])
                        .first()
                    )
                    if db_job:
                        logging.warning(
                            "Job exsisits already. Not creating a new one..."
                        )
                        continue
                    if (
                        "conf_data" in remote_to_client_job
                        and "data_form" in remote_to_client_job["conf_data"]
                        and "identifiers"
                        in remote_to_client_job["conf_data"]["data_form"]
                    ):
                        drop_duplicate_studies = (
                            remote_to_client_job["conf_data"]
                            .get("workflow_form", {})
                            .get("series_uids_with_unique_study_uids", False)
                        )
                        drop_duplicated_patients = (
                            remote_to_client_job["conf_data"]
                            .get("workflow_form", {})
                            .get("series_ids_with_unique_patient_ids", False)
                        )

                        dataset_name = remote_to_client_job["conf_data"]["data_form"][
                            "dataset_name"
                        ]
                        db_dataset = get_dataset(db, dataset_name)
                        if drop_duplicate_studies:
                            identifiers = db_dataset.meta_information[
                                "series_uids_with_unique_study_uids_count"
                            ]["identifiers"]
                            meta_data = db_dataset.meta_information[
                                "series_uids_with_unique_study_uids_count"
                            ]["meta_data"]
                        elif drop_duplicated_patients:
                            identifiers = db_dataset.meta_information[
                                "series_ids_with_unique_patient_ids_count"
                            ]["identifiers"]
                            meta_data = db_dataset.meta_information[
                                "series_ids_with_unique_patient_ids_count"
                            ]["meta_data"]
                        else:
                            identifiers = db_dataset.meta_information["identifiers"][
                                "identifiers"
                            ]
                            meta_data = db_dataset.meta_information["identifiers"][
                                "meta_data"
                            ]

                        remote_to_client_job["conf_data"]["data_form"][
                            "identifiers"
                        ] = [
                            identifiers[idx]
                            for idx in remote_to_client_job["conf_data"]["data_form"][
                                "identifiers"
                            ]
                        ]
                        remote_to_client_job["conf_data"]["data_form"]["meta_data"] = [
                            meta_data[identifier]
                            for identifier in remote_to_client_job["conf_data"][
                                "data_form"
                            ]["identifiers"]
                        ]

                    remote_to_client_job["kaapana_instance_id"] = db_client_kaapana.id
                    remote_to_client_job["owner_kaapana_instance_name"] = (
                        db_remote_kaapana_instance.instance_name
                    )
                    remote_to_client_job["external_job_id"] = remote_to_client_job["id"]
                    remote_to_client_job["status"] = (
                        "pending"
                        if remote_to_client_job["status"] == "created"
                        else remote_to_client_job["status"]
                    )
                    job = schemas.JobCreate(**remote_to_client_job)
                    job.automatic_execution = db_workflow_dict.get(
                        remote_to_client_job["workflow_id"], None
                    ).automatic_execution
                    db_job = create_job(db, job)
                    db_workflow_job_dict[remote_to_client_job["workflow_id"]].append(
                        db_job
                    )

            # Handling incoming job updates
            logging.info("inncoming_update_jobs: " + str(inncoming_update_jobs))
            bulk_update_jobs(db, inncoming_update_jobs)

            # update incoming workflows
            for workflow_id, db_jobs in db_workflow_job_dict.items():
                workflow_update = schemas.WorkflowUpdate(
                    **{
                        "workflow_id": workflow_id,
                        "workflow_jobs": db_jobs,
                    }
                )
                put_workflow_jobs(db, workflow_update)
    except Exception as e:
        client_kaapana_instance = schemas.ClientKaapanaInstanceCreate(
            ssl_check=db_client_kaapana.ssl_check,
            automatic_update=db_client_kaapana.automatic_update,
            automatic_workflow_execution=db_client_kaapana.automatic_workflow_execution,
            fernet_encrypted=db_client_kaapana.fernet_key != "deactivated",
            allowed_dags=[dag for dag in db_client_kaapana.allowed_dags],
            allowed_datasets=[
                dataset["name"] for dataset in db_client_kaapana.allowed_datasets
            ],
            remote_update_log=traceback.format_exc(),
        )
        create_and_update_client_kaapana_instance(
            db=db, client_kaapana_instance=client_kaapana_instance, action="update"
        )
        raise HTTPException(status_code=501, detail=str(e))

    return {f"Executed get remote updates!"}


def sync_states_from_airflow(db: Session, status: str = None, periodically=False):
    # get list from airflow for jobs in status=status: {'dag_run_id': 'state'} -> airflow_jobs_in_qsr_state
    airflow_jobs_in_state = get_dagruns_airflow(tuple([status]))
    # get list from db with all db_jobs in status=status
    db_jobs_in_state = (
        db.query(
            models.Job.id,
            models.Job.run_id,
            models.Job.description,
        )
        .join(models.KaapanaInstance)
        .filter(models.Job.status == status)
        .filter(models.KaapanaInstance.remote == False)
        .all()
    )

    # Convert list of run_id to sets for faster membership checks
    airflow_run_ids = {job["run_id"] for job in airflow_jobs_in_state}
    db_run_ids = {db_job.run_id for db_job in db_jobs_in_state}

    # Find elements which are in current airflow_jobs_runids but not in db_jobs_runids from previous round
    diff_airflow_to_db = [
        job for job in airflow_jobs_in_state if job["run_id"] not in db_run_ids
    ]

    # Find elements which are in db_jobs_runids from previous round but not in current airflow_jobs_runids
    diff_db_to_airflow = [
        db_job for db_job in db_jobs_in_state if db_job.run_id not in airflow_run_ids
    ]

    if len(diff_airflow_to_db) > 0:
        # request airflow for states of all jobs in diff_airflow_to_db && update db_jobs of all jobs in diff_airflow_to_db
        jobs_to_update = []
        for diff_job_af in diff_airflow_to_db:
            # get db_job from db via 'run_id' (fails for all airflow jobs which aren't user-created aka service-jobs)
            db_job = get_job(db, run_id=diff_job_af["run_id"])
            if db_job is not None:
                # update db_job w/ updated state
                job_update = schemas.JobUpdate(
                    **{
                        "job_id": db_job.id,
                        "status": status,
                    }
                )
                jobs_to_update.append(job_update)
            else:
                # should only go into this condition for service-job
                create_and_update_service_workflows_and_jobs(
                    db,
                    diff_job_dagid=diff_job_af["dag_id"],
                    diff_job_runid=diff_job_af["run_id"],
                    status=status,
                )
        bulk_update_jobs(db, jobs_to_update)

    if len(diff_db_to_airflow) > 0:
        run_ids = [
            diff_db_job.run_id
            for diff_db_job in diff_db_to_airflow
            if diff_db_job.run_id is not None
        ]
        # Get diff states:
        try:
            resp = get_dagrun_details_airflow(run_ids)
        except Exception as e:
            logging.error(f"Error while syncing kaapana-backend with Airflow: {e}")
            return
        resp = json.loads(resp.text)

        results = resp.get("results", {})
        warning = resp.get("warning", None)
        if warning:
            logging.error(
                f"Warning in return results syncing kaapana-backend with Airflow: {warning}"
            )
        # update db_jobs of all jobs in diff_db_to_airflow
        jobs_to_update = []
        for diff_db_job in diff_db_to_airflow:
            # update db_job w/ updated state
            if diff_db_job.run_id in results:
                job_update = schemas.JobUpdate(
                    **{
                        "job_id": diff_db_job.id,
                        "description": "The workflow was triggered!",
                        "status": (
                            "finished"
                            if results[diff_db_job.run_id]["state"] == "success"
                            else results[diff_db_job.run_id]["state"]
                        ),
                    }
                )
                jobs_to_update.append(job_update)
            elif status != "scheduled":
                logging.error(f"Job not found in Airflow: {diff_db_job.run_id}")
                tries = 0
                if diff_db_job.description:
                    tries_str = diff_db_job.description.split(" ")[-1]
                    tries = int(tries_str) if tries_str.isdigit() else 0
                tries = tries + 1
                job_update = schemas.JobUpdate(
                    **{
                        "job_id": diff_db_job.id,
                        "description": f"Job not found in Airflow! Try {tries}",
                        "status": status if tries < 6 else "failed",
                    }
                )
                jobs_to_update.append(job_update)

        bulk_update_jobs(db, jobs_to_update)


global_service_jobs = {}


def create_and_update_service_workflows_and_jobs(
    db: Session,
    diff_job_dagid: str = None,
    diff_job_runid: str = None,
    status: str = None,
):
    # additional security buffer to check if current incoming service-job already exists
    # check if service-workflow buffer already exists in global_service_jobs dict
    if diff_job_dagid not in global_service_jobs:
        # if not: add service-workflow buffer
        global_service_jobs[diff_job_dagid] = []
        logging.info(
            f"Add new service-workflow to service-job-buffer mechanism: {diff_job_dagid}"
        )
    # to keep service-workflow lists of gloval_service_jobs small, check whether list exceeds 200 elements, if yes remove oldest 100 elements
    if len(global_service_jobs[diff_job_dagid]) > 200:
        del global_service_jobs[diff_job_dagid][0:99]
    # check if current incoming service-job is already in buffer
    if diff_job_runid in global_service_jobs[diff_job_dagid]:
        # if yes: current incoming service-job will be created in backend --> return
        logging.warn(
            f"Prevented service-jobs from being scheduled multiple times: {diff_job_runid}"
        )
        return
    else:
        # if not: add current incoming service-job to buffer and continue with creating it
        global_service_jobs[diff_job_dagid].append(diff_job_runid)

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
                "workflow_name": db_service_workflow.workflow_name,
                "workflow_jobs": [db_job],
            }
        )
        db_service_workflow = put_workflow_jobs(db, workflow_update)
        logging.debug(f"Updated service workflow: {db_service_workflow}")
    else:
        # if no: compose WorkflowCreate to create service-workflow ...
        workflow_id = (
            f"{''.join([substring[0] for substring in db_job.dag_id.split('-')])}"
        )
        # should normally be not necessary, but additional safety net to not create 2x the same service-workflow
        db_service_workflow = get_workflow(db, dag_id=workflow_id)
        if not db_service_workflow:
            workflow_create = schemas.WorkflowCreate(
                **{
                    "workflow_id": workflow_id,
                    "workflow_name": f"{db_job.dag_id}-{workflow_id}",
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
            logging.info(f"Created service workflow: {db_service_workflow}")
            # ... and afterwards append service-jobs to service-workflow via crud.put_workflow_jobs()
            workflow_update = schemas.WorkflowUpdate(
                **{
                    "workflow_id": db_service_workflow.workflow_id,
                    "workflow_name": db_service_workflow.workflow_name,
                    "workflow_jobs": [db_job],
                }
            )
            db_service_workflow = put_workflow_jobs(db, workflow_update)
            logging.info(f"Updated service workflow: {db_service_workflow}")


def create_or_get_identifier(db: Session, identifier: string) -> models.Identifier:
    try:
        return db.query(models.Identifier).filter_by(id=identifier).one()
    except NoResultFound:
        try:
            with db.begin_nested():
                instance = models.Identifier(id=identifier)
                db.add(instance)
                return instance
        except IntegrityError:
            return db.query(models.Identifier).filter_by(id=identifier).one()


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

    db_identifiers = [create_or_get_identifier(db, idx) for idx in dataset.identifiers]

    db_dataset = models.Dataset(
        username=dataset.username,
        name=dataset.name,
        identifiers=db_identifiers,
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

    db_identifiers = [create_or_get_identifier(db, idx) for idx in dataset.identifiers]

    if dataset.action == "ADD":
        for identifier in db_identifiers:
            if identifier not in db_dataset.identifiers:
                db_dataset.identifiers.append(identifier)
    elif dataset.action == "DELETE":
        for identifier in db_identifiers:
            db_dataset.identifiers.remove(identifier)
    elif dataset.action == "UPDATE":
        db_dataset.identifiers = db_identifiers
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

    # db_kaapana_instance.workflows.append(db_workflow)
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    return db_workflow


# TODO removed async because our current database is not able to execute async methods
# async def queue_generate_jobs_and_add_to_workflow(


def thread_create_objects_and_trigger_workflows(
    jobs_to_create_list: List, workflow=None, workflow_id=None
):
    with SessionLocal() as db:
        db_jobs = []

        for job in jobs_to_create_list:
            db_job = create_job(db, job)
            db_jobs.append(db_job)

        if workflow is not None:
            workflow.workflow_jobs = db_jobs
            db_workflow = create_workflow(db=db, workflow=workflow)
        else:
            db_workflow = get_workflow(db, workflow_id=workflow_id)
            workflow = schemas.WorkflowUpdate(
                **{
                    "workflow_id": db_workflow.workflow_id,
                    "workflow_name": db_workflow.workflow_name,
                    "workflow_jobs": db_jobs,
                }
            )
            db_workflow = put_workflow_jobs(db, workflow)

        if db_workflow.automatic_execution:
            jobs_to_update = []
            for db_job in db_jobs:
                if db_job.kaapana_instance.remote == False:
                    job = schemas.JobUpdate(
                        **{
                            "job_id": db_job.id,
                            "status": "scheduled",
                            "description": "The workflow was triggered!",
                        }
                    )
                    jobs_to_update.append(job)
            bulk_update_jobs(db, jobs_to_update)
        return db_jobs


def queue_generate_jobs_and_add_to_workflow(
    db,
    json_schema_data: schemas.JsonSchemaData,
    workflow: schemas.WorkflowCreate = None,
    use_thread: bool = True,
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
                "instance_names": (
                    conf_data["workflow_form"]["runner_instances"]
                    if not json_schema_data.federated
                    else json_schema_data.instance_names
                ),
            }
        ),
    )
    jobs_to_create_list = []
    for db_kaapana_instance in db_kaapana_instances:
        identifiers = []
        if "data_form" in conf_data and "dataset_name" in conf_data["data_form"]:
            dataset_name = conf_data["data_form"]["dataset_name"]
            if not db_kaapana_instance.remote:
                db_dataset = get_dataset(db, dataset_name)
                identifiers = [idx.id for idx in db_dataset.identifiers]
                conf_data["data_form"].update({"identifiers": identifiers})
            else:
                for dataset_info in db_kaapana_instance.allowed_datasets:
                    if dataset_info["name"] == dataset_name:
                        conf_data["data_form"].update(
                            {
                                "identifiers_count": dataset_info["identifiers_count"],
                                "series_uids_with_unique_study_uids_count": dataset_info[
                                    "series_uids_with_unique_study_uids_count"
                                ],
                                "series_ids_with_unique_patient_ids_count": dataset_info[
                                    "series_ids_with_unique_patient_ids_count"
                                ],
                            }
                        )
                        break

        drop_duplicate_studies = conf_data.get("workflow_form", {}).get(
            "series_uids_with_unique_study_uids", False
        )
        drop_duplicated_patients = conf_data.get("workflow_form", {}).get(
            "series_ids_with_unique_patient_ids", False
        )

        if "data_form" in conf_data and "identifiers" in conf_data["data_form"]:
            # Local instance
            meta_data = get_meta_data(
                conf_data["data_form"]["identifiers"],
                drop_duplicate_studies,
                drop_duplicated_patients,
            )
            conf_data["data_form"]["identifiers"] = list(meta_data.keys())
            conf_data["data_form"]["meta_data"] = meta_data

            # TODO dag running tagging for running series_uids
            # os_processor.queue_operations(instance_ids=tagging, dags_running=[json_schema_data.dag_id])
        elif (
            db_kaapana_instance.remote
            and "data_form" in conf_data
            and "identifiers_count" in conf_data["data_form"]
        ):
            if drop_duplicate_studies:
                conf_data["data_form"]["identifiers"] = list(
                    range(
                        0,
                        conf_data["data_form"][
                            "series_uids_with_unique_study_uids_count"
                        ],
                    )
                )
            elif drop_duplicated_patients:
                conf_data["data_form"]["identifiers"] = list(
                    range(
                        0,
                        conf_data["data_form"][
                            "series_ids_with_unique_patient_ids_count"
                        ],
                    )
                )
            else:
                conf_data["data_form"]["identifiers"] = list(
                    range(0, conf_data["data_form"]["identifiers_count"])
                )

        # compose queued_jobs according to 'single_execution'
        queued_jobs = []
        if single_execution is True:
            for identifier in conf_data["data_form"]["identifiers"][:dataset_limit]:
                # Copying due to reference?!
                single_conf_data = copy.deepcopy(conf_data)
                single_conf_data["data_form"]["identifiers"] = [identifier]
                if "meta_data" in conf_data["data_form"]:
                    single_conf_data["data_form"]["meta_data"] = {
                        identifier: conf_data["data_form"]["meta_data"][identifier]
                    }
                queued_jobs.append(
                    {
                        "conf_data": single_conf_data,
                        "dag_id": json_schema_data.dag_id,
                        "username": username,
                    }
                )
        else:
            check_for_empty_identifiers = conf_data.get("data_form", {}).get(
                "identifiers", None
            )
            if (
                check_for_empty_identifiers is not None
                and len(check_for_empty_identifiers) == 0
            ):
                logging.warning(
                    "No identifiers found in data_form, no job will be created"
                )
                continue
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
                    "status": "created",
                    "kaapana_instance_id": db_kaapana_instance.id,
                    "owner_kaapana_instance_name": settings.instance_name,
                    "automatic_execution": False,
                    "update_external": db_kaapana_instance.remote,
                    **jobs_to_create,
                }
            )
            jobs_to_create_list.append(job)

    if len(jobs_to_create_list) == 0:
        raise HTTPException(status_code=404, detail="No jobs created!")

    if use_thread:
        Thread(
            target=thread_create_objects_and_trigger_workflows,
            args=(
                jobs_to_create_list,
                workflow,
            ),
        ).start()
    else:
        return thread_create_objects_and_trigger_workflows(
            jobs_to_create_list, workflow_id=json_schema_data.workflow_id
        )

    return Response("Workflow and jobs will be created", status_code=200)


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


def thread_bulk_update_jobs(jobs_to_update: List):
    with SessionLocal() as db:
        bulk_update_jobs(db, jobs_to_update)


def update_workflow(db: Session, workflow=schemas.WorkflowUpdate):
    utc_timestamp = get_utc_timestamp()

    db_workflow = get_workflow(db, workflow.workflow_id)
    if db_workflow.federated and workflow.workflow_status == "restart":
        logging.info("Only working with federated workflows!")
        # federated workflow + workflow.workflow_status="scheduled" --> only restart orchestration job and not all jobs of workflow
        job_id = None
        for workflow_job in db_workflow.workflow_jobs:
            if "external_schema_federated_form" in workflow_job.conf_data:
                job_id = workflow_job.id
                break

        if job_id is None:
            logging.error("No orchestration job found in federated workflow!")
            raise HTTPException(
                status_code=404,
                detail="No orchestration job found in federated workflow!",
            )

        db_job = get_job(db, job_id=job_id)
        assert db_job.update_external == False
        job = schemas.JobUpdate(
            **{
                "job_id": job_id,
                "status": workflow.workflow_status,
            }
        )
        bulk_update_jobs(db, [job])
        return db_workflow

    if workflow.workflow_status == "confirmed":
        workflow.workflow_status = "confirmed"
        db_workflow.automatic_execution = True

    # if workflow.workflow_status:  # usually 'scheduled' or 'confirmed'
    #     # iterate over db_jobs in db_workflow ...
    jobs_to_update = []
    for db_workflow_current_job in db_workflow.workflow_jobs:
        job = schemas.JobUpdate(
            job_id=db_workflow_current_job.id,
            update_external=db_workflow_current_job.runs_on_remote,
        )
        assert db_workflow_current_job.update_external == False
        if workflow.workflow_status == "restart":
            if db_workflow_current_job.status in ["failed", "aborted"]:
                job.status = "restart"
                job.description = "The worklow was triggered!"
                jobs_to_update.append(job)
            else:
                logging.warning("Job is not failed, not restarting the job!")
        elif workflow.workflow_status == "aborted":
            job.status = "aborted"
            job.description = "The worklow was aborted!"
            jobs_to_update.append(job)
        elif (
            workflow.workflow_status == "scheduled"
            or workflow.workflow_status == "confirmed"
        ):
            job.status = "scheduled"
            job.description = "The worklow was triggered!"
            jobs_to_update.append(job)
        elif workflow.workflow_status == "deleted":
            job.status = "deleted"
            job.description = "The worklow was deleted!"
            jobs_to_update.append(job)
        else:
            logging.warning("Workflow status not found!")

    Thread(target=thread_bulk_update_jobs, args=(jobs_to_update,)).start()

    db_workflow.time_updated = utc_timestamp
    db.commit()
    db.refresh(db_workflow)

    return db_workflow


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
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if not db_workflow.workflow_jobs:
        db.delete(db_workflow)
        db.commit()
        return {
            "type": "success",
            "title": "Successfully deleted workflow with all its jobs.",
        }

    workflow_update = schemas.WorkflowUpdate(**db_workflow.__dict__)
    workflow_update.workflow_status = "deleted"
    try:
        db_workflow = update_workflow(db, workflow_update)
    except AssertionError as e:
        return {
            "type": "warning",
            "title": f"Some of the jobs are currently updating, please try again, once the update finished.",
        }
    # iterate over jobs of to-be-deleted workflow
    return {
        "type": "warning",
        "title": f"Jobs in state 'created', 'pending', 'finished', 'aborted' or 'failed' will be deleted. The workflow item can only be deleted, if it contains no job items.",
    }


def delete_workflows(db: Session):
    # TODO: add remote workflow deletion
    db.query(models.Workflow).delete()
    db.commit()
    return {"ok": True}
