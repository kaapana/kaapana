from ast import alias
import json
from typing import List
from urllib import request
import uuid
import requests
import os

from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from psycopg2.errors import UniqueViolation
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, Request, HTTPException, Response

from . import models, schemas
from app.config import settings
from .schemas import Identifier
from .utils import execute_job_airflow, abort_job_airflow, check_dag_id_and_dataset, get_utc_timestamp, HelperMinio, get_dag_list, \
    raise_kaapana_connection_error, requests_retry_session, get_uid_list_from_query
from urllib3.util import Timeout

TIMEOUT_SEC = 5
TIMEOUT = Timeout(TIMEOUT_SEC)


def delete_kaapana_instance(db: Session, kaapana_instance_id: int):
    db_kaapana_instance = db.query(models.KaapanaInstance).filter_by(id=kaapana_instance_id).first()
    if not db_kaapana_instance:
        raise HTTPException(status_code=404, detail="Kaapana instance not found")
    db.delete(db_kaapana_instance)
    db.commit()
    return {"ok": True}


def delete_kaapana_instances(db: Session):
    db.query(models.KaapanaInstance).delete()
    db.commit()
    return {"ok": True}


def get_kaapana_instance(db: Session, instance_name: str = None, remote: bool = True):
    return db.query(models.KaapanaInstance).filter_by(instance_name=instance_name or settings.instance_name,
                                                      remote=remote).first()


def get_kaapana_instances(db: Session, filter_kaapana_instances: schemas.FilterKaapanaInstances = None):
    if filter_kaapana_instances.instance_names:
        return db.query(models.KaapanaInstance).filter(models.KaapanaInstance.remote == filter_kaapana_instances.remote,
                                                       models.KaapanaInstance.instance_name.in_(
                                                           filter_kaapana_instances.instance_names)).all()
    elif filter_kaapana_instances.dag_id is not None:
        return db.query(models.KaapanaInstance).filter(models.KaapanaInstance.remote == filter_kaapana_instances.remote,
                                                       models.KaapanaInstance.allowed_dags.contains(
                                                           filter_kaapana_instances.dag_id)).all()
    elif filter_kaapana_instances.instance_names and filter_kaapana_instances.dag_id is not None:
        return db.query(models.KaapanaInstance).filter(models.KaapanaInstance.remote == filter_kaapana_instances.remote,
                                                       models.KaapanaInstance.allowed_dags.contains(
                                                           filter_kaapana_instances.dag_id),
                                                       models.KaapanaInstance.instance_name.in_(
                                                           filter_kaapana_instances.instance_names)).all()
    else:
        return db.query(models.KaapanaInstance).filter_by(remote=filter_kaapana_instances.remote).all()


def create_and_update_client_kaapana_instance(db: Session, client_kaapana_instance: schemas.ClientKaapanaInstanceCreate,
                                              action='create'):
    def _get_fernet_key(fernet_encrypted):
        if fernet_encrypted is True:
            return Fernet.generate_key().decode()
        else:
            return 'deactivated'

    utc_timestamp = get_utc_timestamp()
    allowed_dags = json.dumps(
        get_dag_list(only_dag_names=False, filter_allowed_dags=client_kaapana_instance.allowed_dags))
    allowed_datasets = json.dumps(
        [dataset for dataset in client_kaapana_instance.allowed_datasets if dataset in get_cohorts(db)])
    db_client_kaapana_instance = get_kaapana_instance(db, remote=False)
    if action == 'create':
        if db_client_kaapana_instance:
            raise HTTPException(status_code=400, detail="Kaapana instance already exists!")

    if action == 'create':
        db_client_kaapana_instance = models.KaapanaInstance(
            instance_name=settings.instance_name,
            token=str(uuid.uuid4()),
            protocol='https',
            host=settings.hostname,
            port=int(os.getenv('HTTPS_PORT', 443)),
            ssl_check=client_kaapana_instance.ssl_check,
            fernet_key=_get_fernet_key(client_kaapana_instance.fernet_encrypted),
            remote=False,
            allowed_dags=allowed_dags,
            allowed_datasets=allowed_datasets,
            time_created=utc_timestamp,
            time_updated=utc_timestamp,
            automatic_update=client_kaapana_instance.automatic_update or False,
            automatic_job_execution=client_kaapana_instance.automatic_job_execution or False
        )
    elif action == 'update':
        if db_client_kaapana_instance.fernet_key == 'deactivated' and client_kaapana_instance.fernet_encrypted is True:
            db_client_kaapana_instance.fernet_key = _get_fernet_key(client_kaapana_instance.fernet_encrypted)
        elif db_client_kaapana_instance.fernet_key != 'deactivated' and client_kaapana_instance.fernet_encrypted is False:
            db_client_kaapana_instance.fernet_key = 'deactivated'
        db_client_kaapana_instance.ssl_check = client_kaapana_instance.ssl_check
        db_client_kaapana_instance.allowed_dags = allowed_dags
        db_client_kaapana_instance.allowed_datasets = allowed_datasets
        db_client_kaapana_instance.automatic_update = client_kaapana_instance.automatic_update or False
        db_client_kaapana_instance.automatic_job_execution = client_kaapana_instance.automatic_job_execution or False
    else:
        raise NameError('action must be one of create, update')

    print("Updating Kaapana Instance successful!")

    db.add(db_client_kaapana_instance)
    db.commit()
    db.refresh(db_client_kaapana_instance)
    return db_client_kaapana_instance


def create_and_update_remote_kaapana_instance(db: Session, remote_kaapana_instance: schemas.RemoteKaapanaInstanceCreate,
                                              action='create'):
    utc_timestamp = get_utc_timestamp()
    db_remote_kaapana_instance = get_kaapana_instance(db, remote_kaapana_instance.instance_name, remote=True)
    if action == 'create':
        if db_remote_kaapana_instance:
            raise HTTPException(status_code=400, detail="Kaapana instance already exists!")
    if action == 'create':
        db_remote_kaapana_instance = models.KaapanaInstance(
            instance_name=remote_kaapana_instance.instance_name,
            token=remote_kaapana_instance.token,
            protocol='https',
            host=remote_kaapana_instance.host,
            port=remote_kaapana_instance.port,
            ssl_check=remote_kaapana_instance.ssl_check,
            fernet_key=remote_kaapana_instance.fernet_key or 'deactivated',
            remote=True,
            time_created=utc_timestamp,
            time_updated=utc_timestamp
        )
    elif action == 'update':
        db_remote_kaapana_instance.token = remote_kaapana_instance.token
        db_remote_kaapana_instance.port = remote_kaapana_instance.port
        db_remote_kaapana_instance.ssl_check = remote_kaapana_instance.ssl_check
        db_remote_kaapana_instance.fernet_key = remote_kaapana_instance.fernet_key or 'deactivated'
        db_remote_kaapana_instance.time_updated = utc_timestamp
    elif action == 'external_update':
        print(f"Externally updating with db_remote_kaapana_instance: {db_remote_kaapana_instance}")
        if db_remote_kaapana_instance:
            db_remote_kaapana_instance.allowed_dags = json.dumps(remote_kaapana_instance.allowed_dags)
            db_remote_kaapana_instance.allowed_datasets = json.dumps(remote_kaapana_instance.allowed_datasets)
            db_remote_kaapana_instance.automatic_update = remote_kaapana_instance.automatic_update or False
            db_remote_kaapana_instance.automatic_job_execution = remote_kaapana_instance.automatic_job_execution or False
            db_remote_kaapana_instance.time_updated = utc_timestamp
        else:
            return Response("Your instance name differs from the remote instance name!", 200)
    else:
        raise NameError('action must be one of create, update, external_update')
    db.add(db_remote_kaapana_instance)
    db.commit()
    db.refresh(db_remote_kaapana_instance)
    return db_remote_kaapana_instance


def create_job(db: Session, job: schemas.JobCreate):
    db_kaapana_instance = db.query(models.KaapanaInstance).filter_by(id=job.kaapana_instance_id).first()
    if not db_kaapana_instance:
        raise HTTPException(status_code=404, detail="Kaapana instance not found")

    if db_kaapana_instance.remote is True and 'federated_form' in job.conf_data and \
            ('federated_dir' in job.conf_data['federated_form'] and \
             'federated_bucket' in job.conf_data['federated_form'] and \
             'federated_operators' in job.conf_data['federated_form']):
        minio_urls = HelperMinio.add_minio_urls(
            job.conf_data['federated_form'],
            db_kaapana_instance.instance_name
        )
        print('minio_urls ', minio_urls)
        job.conf_data['federated_form']['minio_urls'] = minio_urls

    print('db_kaapana_instance.automatic_job_execution')

    utc_timestamp = get_utc_timestamp()

    print(f"JobCreate: {job}")
    db_job = models.Job(
        conf_data=json.dumps(job.conf_data),
        time_created=utc_timestamp,
        time_updated=utc_timestamp,
        external_job_id=job.external_job_id,
        username=job.username,
        dag_id=job.dag_id,
        kaapana_id=job.kaapana_instance_id,
        owner_kaapana_instance_name=job.owner_kaapana_instance_name,    # replaced addressed_kaapana_instance_name w/ owner_kaapana_instance_name or None
        status=job.status
    )

    db_kaapana_instance.jobs.append(db_job)
    db.add(db_kaapana_instance)
    try:
        db.commit()  # writing, if kaapana_id and external_job_id already exists will fail due to duplicate error
    except IntegrityError as e:
        assert isinstance(e.orig, UniqueViolation)  # proves the original exception
        return db.query(models.Job).filter_by(external_job_id=db_job.external_job_id,
                                              owner_kaapana_instance_name=db_job.owner_kaapana_instance_name).first()

    update_external_job(db, db_job) # does nothing if db_job.external_job_id is None
    db.refresh(db_job)
    if db_kaapana_instance.remote is False and db_kaapana_instance.automatic_job_execution is True:
        job = schemas.JobUpdate(**{
            'job_id': db_job.id,
            'status': 'scheduled',
            'description': 'The worklow was triggered!'
        })
        update_job(db, job, remote=False)
        print('scheduled')

    return db_job


def get_job(db: Session, job_id: int):
    db_job = db.query(models.Job).filter_by(id=job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job


def delete_job(db: Session, job_id: int, remote: bool = True):
    db_job = get_job(db, job_id)
    if (db_job.experiment.kaapana_instance.remote != remote) and db_job.status not in ["queued", "finished", "failed"]:
        raise HTTPException(status_code=401, detail="You are not allowed to delete this job, since its on the client site")
    delete_external_job(db, db_job)
    db.delete(db_job)
    db.commit()
    return {"ok": True}


def delete_jobs(db: Session):
    # Todo add remote job deletion
    db.query(models.Job).delete()
    db.commit()
    return {"ok": True}


def get_jobs(db: Session, instance_name: str = None, status: str = None, remote: bool = True, limit=None):
    if instance_name is not None and status is not None:
        # org: return db.query(models.Job).filter_by(status=status).join(models.Job.kaapana_instance, aliased=True).filter_by(instance_name=instance_name, remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()
        # w/ experiment: return db.query(models.Job).filter_by(status=status).join(models.Job.experiment, aliased=True).join(models.Experiment.kaapana_instance, aliased=True).filter_by(instance_name=instance_name, remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all() # doesn't work for job querying in remote/federated job execution
        return db.query(models.Job).filter_by(status=status).join(models.Job.kaapana_instance, aliased=True).filter_by(instance_name=instance_name).order_by(desc(models.Job.time_updated)).limit(limit).all()  # same as org but w/o filtering by remote
    elif instance_name is not None:
        # org: return db.query(models.Job).join(models.Job.kaapana_instance, aliased=True).filter_by(instance_name=instance_name, remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()
        # w/ experiment: return db.query(models.Job).join(models.Job.experiment, aliased=True).join(models.Experiment.kaapana_instance, aliased=True).filter_by(instance_name=instance_name, remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()
        return db.query(models.Job).join(models.Job.kaapana_instance, aliased=True).filter_by(instance_name=instance_name).order_by(desc(models.Job.time_updated)).limit(limit).all()  # same as org but w/o filtering by remote
    elif status is not None:
        # org: return db.query(models.Job).filter_by(status=status).join(models.Job.kaapana_instance, aliased=True).filter_by(remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()
        # w/ experiment: return db.query(models.Job).filter_by(status=status).join(models.Job.experiment, aliased=True).join(models.Experiment.kaapana_instance, aliased=True).filter_by(remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()
        return db.query(models.Job).filter_by(status=status).join(models.Job.kaapana_instance, aliased=True).order_by(desc(models.Job.time_updated)).limit(limit).all()  # same as org but w/o filtering by remote
    else:
        # org: return db.query(models.Job).join(models.Job.kaapana_instance, aliased=True).filter_by(remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()
        return db.query(models.Job).join(models.Job.experiment, aliased=True).join(models.Experiment.kaapana_instance, aliased=True).filter_by(remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()
        # explanation: db.query(models.Job) returns a Query object; .join() creates more narrow Query objects ; filter_by() applies the filter criterion to the remaining Query (source: https://docs.sqlalchemy.org/en/14/orm/query.html#sqlalchemy.orm.Query)

def update_job(db: Session, job=schemas.JobUpdate, remote: bool = True):
    utc_timestamp = get_utc_timestamp()

    print(f'Updating client job {job.job_id} with job.status: {job.status}')
    db_job = get_job(db, job.job_id)

    if (job.status == 'scheduled' and db_job.kaapana_instance.remote == False): #  or (job.status == 'failed'); status='scheduled' for restarting, status='failed' for aborting
        print(f'Executing  job {db_job.id}')
        conf_data = json.loads(db_job.conf_data)
        conf_data['client_job_id'] = db_job.id
        print("db_job.kaapana_instance:", db_job.kaapana_instance, "db_job.dag_id", db_job.dag_id, 
              "db_job.owner_kaapana_instance_name", db_job.owner_kaapana_instance_name)
        dag_id_and_dataset = check_dag_id_and_dataset(db_job.kaapana_instance, conf_data, db_job.dag_id,
                                                      db_job.owner_kaapana_instance_name)
        print("dag_id_and_dataset:", dag_id_and_dataset)
        if dag_id_and_dataset is not None:
            job.status = 'failed'
            job.description = dag_id_and_dataset
        else:
            print("update_job() right before execute_job()")
            execute_job_airflow(conf_data, db_job)

    if (db_job.kaapana_instance.remote != remote) and db_job.status not in ["queued", "finished", "failed"]:
        raise HTTPException(status_code=401,
                            detail="You are not allowed to update this job, since its on the client site")
    db_job.status = job.status
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
    print(f"Aborting job {job}")
    # print(f'Aborting client job {job.job_id} with job.status: {job.status}')
    db_job = get_job(db, job.job_id)    # should actually be job.job_id instead of just job but somehow (unfortunately) works ...
    conf_data = json.loads(db_job.conf_data)
    conf_data['client_job_id'] = db_job.id

    abort_job_airflow(db_job.dag_id, db_job.run_id, db_job.status, conf_data)


def sync_client_remote(db: Session, remote_kaapana_instance: schemas.RemoteKaapanaInstanceUpdateExternal,
                       instance_name: str = None, status: str = None):
    db_client_kaapana = get_kaapana_instance(db, remote=False)

    create_and_update_remote_kaapana_instance(
        db=db, remote_kaapana_instance=remote_kaapana_instance, action='external_update')
    print(f"SYNC_CLIENT_REMOTE for instance_name: {instance_name} ; status: {status}")
    db_incoming_jobs = get_jobs(db, instance_name=instance_name, status=status, remote=True)
    incoming_jobs = [schemas.Job(**job.__dict__).dict() for job in db_incoming_jobs]
    print(f"SYNC_CLIENT_REMOTE imcoming_jobs: {incoming_jobs}")

    update_remote_instance_payload = {
        "instance_name": db_client_kaapana.instance_name,
        "allowed_dags": json.loads(db_client_kaapana.allowed_dags),
        "allowed_datasets": json.loads(db_client_kaapana.allowed_datasets),
        "automatic_update": db_client_kaapana.automatic_update,
        "automatic_job_execution": db_client_kaapana.automatic_job_execution
    }
    return {
        'incoming_jobs': incoming_jobs,
        'update_remote_instance_payload': update_remote_instance_payload
    }


def delete_external_job(db: Session, db_job):
    if db_job.external_job_id is not None:
        print(f'Deleting remote job {db_job.external_job_id}, {db_job.owner_kaapana_instance_name}')
        same_instance = db_job.owner_kaapana_instance_name == settings.instance_name
        db_remote_kaapana_instance = get_kaapana_instance(db, instance_name=db_job.owner_kaapana_instance_name,
                                                          remote=True)
        params = {
            "job_id": db_job.external_job_id,
        }
        if same_instance:
            delete_job(db, **params)
        else:
            remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/kaapana-backend/remote'
            with requests.Session() as s:
                r = requests_retry_session(session=s).delete(f'{remote_backend_url}/job',
                                                             verify=db_remote_kaapana_instance.ssl_check, params=params,
                                                             headers={
                                                                 'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'},
                                                             timeout=TIMEOUT)
            if r.status_code == 404:
                print(f'External job {db_job.external_job_id} does not exist')
            else:
                raise_kaapana_connection_error(r)
                print(r.json())


def update_external_job(db: Session, db_job):
    if db_job.external_job_id is not None:
        print(f'Updating remote job {db_job.external_job_id}, {db_job.owner_kaapana_instance_name}')
        same_instance = db_job.owner_kaapana_instance_name == settings.instance_name    # will be the same !
        db_remote_kaapana_instance = get_kaapana_instance(db, instance_name=db_job.owner_kaapana_instance_name,
                                                          remote=True)
        payload = {
            "job_id": db_job.external_job_id,
            "run_id": db_job.run_id,
            "status": db_job.status,
            "description": db_job.description
        }
        if same_instance:
            update_job(db, schemas.JobUpdate(**payload))
        else:
            remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/kaapana-backend/remote'
            with requests.Session() as s:
                r = requests_retry_session(session=s).put(f'{remote_backend_url}/job',
                                                          verify=db_remote_kaapana_instance.ssl_check, json=payload,
                                                          headers={
                                                              'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'},
                                                          timeout=TIMEOUT)
            if r.status_code == 404:
                print(f'External job {db_job.external_job_id} does not exist')
            else:
                raise_kaapana_connection_error(r)
                print(r.json())


def get_remote_updates(db: Session, periodically=False):
    print("WE'RE GETTING REMOTE UPDATES!!!")
    db_client_kaapana = get_kaapana_instance(db, remote=False)
    print(f"db_client_kaapana: {db_client_kaapana}")
    if periodically is True and db_client_kaapana.automatic_update is False:
        return
    db_remote_kaapana_instances = get_kaapana_instances(db, filter_kaapana_instances=schemas.FilterKaapanaInstances(
        **{'remote': True}))
    print(f"db_remote_kaapana_instances: {db_remote_kaapana_instances}")
    for db_remote_kaapana_instance in db_remote_kaapana_instances:
        same_instance = db_remote_kaapana_instance.instance_name == settings.instance_name
        update_remote_instance_payload = {
            "instance_name": db_client_kaapana.instance_name,
            "allowed_dags": json.loads(db_client_kaapana.allowed_dags),
            "allowed_datasets": json.loads(db_client_kaapana.allowed_datasets),
            "automatic_update": db_client_kaapana.automatic_update,
            "automatic_job_execution": db_client_kaapana.automatic_job_execution
        }

        job_params = {
            "instance_name": db_client_kaapana.instance_name,
            "status": "queued"
        }
        if same_instance is True:
            incoming_data = sync_client_remote(db=db,
                                               remote_kaapana_instance=schemas.RemoteKaapanaInstanceUpdateExternal(
                                                   **update_remote_instance_payload), **job_params)
        else:
            remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/kaapana-backend/remote'
            print(f"remote_backend_url: {remote_backend_url}")
            # print(f"job_params in params: {job_params}")
            # print(f"update_remote_instance_payload in json: {update_remote_instance_payload}")
            with requests.Session() as s:
                r = requests_retry_session(session=s).put(f'{remote_backend_url}/sync-client-remote', params=job_params,
                                                          json=update_remote_instance_payload,
                                                          verify=db_remote_kaapana_instance.ssl_check,
                                                          headers={
                                                              'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'},
                                                          timeout=TIMEOUT)
            if r.status_code == 405:
                print(f'Warning!!! We could not reach the following backend {db_remote_kaapana_instance.host}')
                continue
            raise_kaapana_connection_error(r)
            incoming_data = r.json()
        incoming_jobs = incoming_data['incoming_jobs']
        print(f"incoming_jobs: {incoming_jobs}") # \n incoming_data: {incoming_data}")
        remote_kaapana_instance = schemas.RemoteKaapanaInstanceUpdateExternal(
            **incoming_data['update_remote_instance_payload'])

        create_and_update_remote_kaapana_instance(db=db, remote_kaapana_instance=remote_kaapana_instance,
                                                  action='external_update')

        for incoming_job in incoming_jobs:
            print('Creating', incoming_job["id"])
            incoming_job['kaapana_instance_id'] = db_client_kaapana.id
            incoming_job['owner_kaapana_instance_name'] = db_remote_kaapana_instance.instance_name
            incoming_job['external_job_id'] = incoming_job["id"]
            incoming_job['status'] = "pending"
            job = schemas.JobCreate(**incoming_job)
            db_job = create_job(db, job)

    return  # schemas.RemoteKaapanaInstanceUpdateExternal(**udpate_instance_payload)


def create_identifier(db: Session, identifier: schemas.Identifier):
    db_identifier = models.Identifier(
        identifier=identifier.identifier
    )
    db.add(db_identifier)
    db.commit()
    db.refresh(db_identifier)
    return db_identifier


def get_identifiers(db: Session):
    return db.query(models.Identifier).all()


def get_identifier(db: Session, identifier: str):
    return db.query(models.Identifier).filter_by(identifier=identifier).first()


def delete_identifier(db: Session, identifier: str):
    db_identifier = get_identifier(db, identifier)
    db.delete(db_identifier)
    db.commit()
    return {"ok": True}


def delete_identifiers(db: Session):
    items = db.query(models.Identifier).all()
    [db.delete(item) for item in items]
    db.commit()
    return {"ok": True}


def create_cohort(db: Session, cohort: schemas.CohortCreate):
    if cohort.kaapana_instance_id is None:
        db_kaapana_instance = db.query(models.KaapanaInstance).filter_by(remote=False).first()
    else:
        db_kaapana_instance = db.query(models.KaapanaInstance).filter_by(id=cohort.kaapana_instance_id).first()

    if db.query(models.Cohort).filter_by(cohort_name=cohort.cohort_name).first():
        raise HTTPException(status_code=409, detail="Cohort exists already!")

    if not db_kaapana_instance:
        raise HTTPException(status_code=404, detail="Kaapana instance not found")

    utc_timestamp = get_utc_timestamp()

    if cohort.cohort_query and not cohort.cohort_identifiers:
        db_cohort_identifiers: List[models.Identifier] = [
            get_identifier(db, identifier)
            for identifier in get_uid_list_from_query(cohort.cohort_query)
        ]
    else:
        db_cohort_identifiers: List[models.Identifier] = [
            get_identifier(db, identifier.identifier)
            for identifier in cohort.cohort_identifiers
        ]

    print('identifiers: ', db_cohort_identifiers)

    db_cohort = models.Cohort(
        username=cohort.username,
        cohort_name=cohort.cohort_name,
        cohort_query=json.dumps(cohort.cohort_query),
        cohort_identifiers=db_cohort_identifiers,
        time_created=utc_timestamp,
        time_updated=utc_timestamp
    )

    db_kaapana_instance.cohorts.append(db_cohort)
    db.add(db_kaapana_instance)
    db.commit()
    db.refresh(db_cohort)
    return db_cohort


def get_cohort(db: Session, cohort_name: str):
    db_cohort = db.query(models.Cohort).filter_by(cohort_name=cohort_name).first()
    if not db_cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    return db_cohort


def get_cohorts(db: Session, instance_name: str = None, limit=None, as_list: bool = True, username: str = None):
    print(username)
    if username is not None:
        db_cohorts = db.query(models.Cohort).filter_by(username=username).join(models.Cohort.kaapana_instance,
                                                                               aliased=True).order_by(
            desc(models.Cohort.time_updated)).limit(limit).all()
    else:
        db_cohorts = db.query(models.Cohort).join(models.Cohort.kaapana_instance, aliased=True).order_by(
            desc(models.Cohort.time_updated)).limit(limit).all()
    if as_list is True:
        return [db_cohort.cohort_name for db_cohort in db_cohorts]
    return db_cohorts


def delete_cohort(db: Session, cohort_name: str):
    db_cohort = get_cohort(db, cohort_name)
    db.delete(db_cohort)
    db.commit()
    return {"ok": True}


def delete_cohorts(db: Session):
    items = db.query(models.Cohort).all()
    [db.delete(item) for item in items]
    db.commit()
    return {"ok": True}


def update_cohort(db: Session, cohort=schemas.CohortUpdate):
    utc_timestamp = get_utc_timestamp()

    print(f'Updating cohort {cohort.cohort_name}')
    db_cohort = get_cohort(db, cohort.cohort_name)

    if cohort.cohort_name is not None:
        db_cohort.cohort_name = cohort.cohort_name

    if cohort.cohort_query and not cohort.cohort_identifiers:
        cohort.cohort_identifiers = get_uid_list_from_query(cohort.cohort_query)
    # TODO: probably have to retrieve them from the db

    db_identifiers = [
        get_identifier(db, identifier.identifier)
        for identifier in cohort.cohort_identifiers
    ]

    if cohort.action == 'ADD':
        db_cohort.cohort_identifiers = list(set(db_identifiers + db_cohort.cohort_identifiers))
    elif cohort.action == 'DELETE':
        db_cohort.cohort_identifiers = [
            identifier
            for identifier in db_cohort.cohort_identifiers
            if identifier not in db_identifiers
        ]
    elif cohort.action == 'UPDATE':
        db_cohort.cohort_identifiers = db_identifiers
    else:
        raise ValueError(f'Invalid action {cohort.action}')

    # db_cohort.username = username
    db_cohort.cohort_query = json.dumps(cohort.cohort_query)
    db.commit()
    db.refresh(db_cohort)
    return db_cohort

def create_experiment(db: Session, experiment: schemas.ExperimentCreate):
    
    if experiment.kaapana_instance_id is None:  # experiment has a kaapana_instance_id?
        db_kaapana_instance = db.query(models.KaapanaInstance).filter_by(remote=False).first()  # no: take first element on non-remote Kaapana instances in db
    else:
        db_kaapana_instance = db.query(models.KaapanaInstance).filter_by(id=experiment.kaapana_instance_id).first() # yes: search Kaapana instance in db according to given kaapana_instance_id
    
    print("We're right before models.Experiment querying!")
    if db.query(models.Experiment).filter_by(experiment_name=experiment.experiment_name).first():   # experiment already exists?
        raise HTTPException(status_code=409, detail="Experiment exists already!")                   # ... raise http exception!
    if not db_kaapana_instance:                                                                     # no kaapana_instance found in db in previous "search"?
        raise HTTPException(status_code=404, detail="Kaapana instance not found")                   # ... raise http exception!
    
    utc_timestamp = get_utc_timestamp()

    print(f"We're right before creation of models.Experiment!")
    print(f"kaapana_id={experiment.kaapana_instance_id} ; username={experiment.username} ; experiment_name={experiment.experiment_name} ; experiment_jobs={experiment.experiment_jobs}")
    db_experiment = models.Experiment(
        kaapana_id=experiment.kaapana_instance_id,
        username=experiment.username,
        experiment_name=experiment.experiment_name,
        experiment_jobs=experiment.experiment_jobs,                   # list experiment_jobs already added to experiment in client.py's def create_experiment()
        # involved_kaapana_instances = experiment.involved_kaapana_instances,
        cohort_name=experiment.cohort_name,
        time_created=utc_timestamp,
        time_updated=utc_timestamp
    )
    print(f"models.Experiment.time_created: {db_experiment.time_created}")  # still working
    print("db_experiment successfully created!")    # still working

    # TODO: also update all involved_kaapana_instances with the experiment_id in which they are involved

    db_kaapana_instance.experiments.append(db_experiment)
    db.add(db_kaapana_instance)
    db.commit()
    db.refresh(db_experiment)
    return db_experiment

def get_experiment(db: Session, experiment_id: int):
    db_experiment = db.query(models.Experiment).filter_by(id=experiment_id).first()
    if not db_experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return db_experiment

def get_experiments(db: Session, instance_name: str = None, limit=None):
    if instance_name is not None:
        return db.query(models.Experiment).join(models.Experiment.kaapana_instance, aliased=True).filter_by(instance_name=instance_name).order_by(desc(models.Experiment.time_updated)).limit(limit).all()
    else:
        return db.query(models.Experiment).join(models.Experiment.kaapana_instance).order_by(desc(models.Experiment.time_updated)).limit(limit).all()   # , aliased=True

def get_experiment_jobs(db: Session, experiment_name: str = None, status: str = None, limit=None):
    # print("Job's status: ", status)
    if experiment_name is not None and status is not None:
        return db.query(models.Job).filter_by(status=status).join(models.Job.experiment, aliased=True).filter_by(experiment_name=experiment_name).order_by(desc(models.Job.time_updated)).limit(limit).all()
    elif experiment_name is not None:
        return db.query(models.Job).join(models.Job.experiment, aliased=True).filter_by(experiment_name=experiment_name).order_by(desc(models.Job.time_updated)).limit(limit).all()
        # from get_jobs: org: return db.query(models.Job).join(models.Job.kaapana_instance, aliased=True).filter_by(instance_name=instance_name, remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()
        # from get_jobs: return db.query(models.Job).join(models.Job.experiment, aliased=True).join(models.Experiment.kaapana_instance, aliased=True).filter_by(instance_name=instance_name, remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()
    # third case not necessary since experiment has no remote argument so far
    elif status is not None:
        return db.query(models.Job).filter_by(status=status).join(models.Job.experiment, aliased=True).order_by(desc(models.Job.time_updated)).limit(limit).all()
    else:
        return db.query(models.Job).join(models.Job.experiment, aliased=True).order_by(desc(models.Job.time_updated)).limit(limit).all()

def update_experiment(db: Session, experiment=schemas.ExperimentUpdate):
    utc_timestamp = get_utc_timestamp()

    print(f'Updating client experiment {experiment.experiment_id} in status: {experiment.experiment_status}')
    db_experiment = get_experiment(db, experiment.experiment_id)

    if experiment.experiment_status != "abort":
        for db_experiment_current_job in db_experiment.experiment_jobs:    # iterate over db_jobs in db_experiment ...
            # either update db_jobs on own kaapana_instance
            if db_experiment.kaapana_instance.remote is False and db_experiment.kaapana_instance.automatic_job_execution is True:
                job = schemas.JobUpdate(**{
                    'job_id': db_experiment_current_job.id,
                    'status': 'scheduled',
                    'description':'The worklow was triggered!'
                    })
                update_job(db, job, remote=False)   # def update_job() expects job of class schemas.JobUpdate
                print('scheduled')

            # or update db_jobs on remote kaapana_instance
            elif db_experiment.kaapana_instance.remote is True and db_experiment.kaapana_instance.automatic_job_execution is True:    
                update_external_job(db, db_experiment_current_job)  # def update_external_job expects db_experiment_current_job of class models.Job

            else:
                raise HTTPException(status_code=404, detail="Job updating while updating the experiment failed!")

    db_experiment.time_updated = utc_timestamp
    db.commit()
    db.refresh(db_experiment)

    return db_experiment

def delete_experiment(db: Session, experiment_id: int):
    db_experiment = get_experiment(db, experiment_id)   # get db's db_experiment object

    # iterate over jobs of to-be-deleted experiment
    for db_experiment_current_job in db_experiment.experiment_jobs:
        delete_job(db, job_id=db_experiment_current_job.id, remote=False)   # deletes local and remote jobs

    db.delete(db_experiment)
    db.commit()
    return {"ok": True}

def delete_experiments(db: Session):
    # TODO: add remote experiment deletion
    db.query(models.Experiment).delete()
    db.commit()
    return {"ok": True}
