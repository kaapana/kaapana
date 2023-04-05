import json
import os
import logging
import traceback
import uuid
import copy
from typing import List

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
from .utils import execute_job_airflow, abort_job_airflow, get_dagrun_tasks_airflow, \
    get_dagrun_details_airflow, get_dagruns_airflow, check_dag_id_and_dataset, get_utc_timestamp, \
        HelperMinio, get_dag_list, raise_kaapana_connection_error, requests_retry_session, get_uid_list_from_query

logging.getLogger().setLevel(logging.INFO)

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
        db_client_kaapana_instance.time_updated = utc_timestamp
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

    logging.info("Updating Kaapana Instance successful!")

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
        logging.info(f"Externally updating with db_remote_kaapana_instance: {db_remote_kaapana_instance}")
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
        job.conf_data['federated_form']['minio_urls'] = minio_urls

    utc_timestamp = get_utc_timestamp()

    db_job = models.Job(
        # id = job.id,    # not sure if this shouldn't be set automatically
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

    return db_job


def get_job(db: Session, job_id: int = None, run_id: str = None):
    if job_id is not None:
        db_job = db.query(models.Job).filter_by(id=job_id).first()
    elif run_id is not None:
        db_job = db.query(models.Job).filter_by(run_id=run_id).first()
    # if not db_job:
    else:
        logging.warning(f"No job found in db with job_id={job_id}, run_id={run_id} --> will return None")
        return None
        # raise HTTPException(status_code=404, detail="Job not found")
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


def get_jobs(db: Session, instance_name: str = None, experiment_name: str = None, status: str = None, remote: bool = True, limit=None):
    if instance_name is not None and status is not None:
        return db.query(models.Job).filter_by(status=status).join(models.Job.kaapana_instance, aliased=True).filter_by(instance_name=instance_name).order_by(desc(models.Job.time_updated)).limit(limit).all()  # same as org but w/o filtering by remote
    elif experiment_name is not None and status is not None:
        return db.query(models.Job).filter_by(status=status).join(models.Job.experiment, aliased=True).filter_by(experiment_name=experiment_name).order_by(desc(models.Job.time_updated)).limit(limit).all()
    elif instance_name is not None:
        return db.query(models.Job).join(models.Job.kaapana_instance, aliased=True).filter_by(instance_name=instance_name).order_by(desc(models.Job.time_updated)).limit(limit).all()  # same as org but w/o filtering by remote
    elif experiment_name is not None:
        return db.query(models.Job).join(models.Job.experiment, aliased=True).filter_by(experiment_name=experiment_name).order_by(desc(models.Job.time_updated)).limit(limit).all()
    elif status is not None:
        return db.query(models.Job).filter_by(status=status).join(models.Job.kaapana_instance, aliased=True).order_by(desc(models.Job.time_updated)).limit(limit).all()  # same as org but w/o filtering by remote
    else:
        return db.query(models.Job).join(models.Job.experiment, aliased=True).join(models.Experiment.kaapana_instance, aliased=True).filter_by(remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()
        # explanation: db.query(models.Job) returns a Query object; .join() creates more narrow Query objects ; filter_by() applies the filter criterion to the remaining Query (source: https://docs.sqlalchemy.org/en/14/orm/query.html#sqlalchemy.orm.Query)

def update_job(db: Session, job=schemas.JobUpdate, remote: bool = True):
    utc_timestamp = get_utc_timestamp()

    db_job = get_job(db, job.job_id, job.run_id)

    # update jobs of own db which are remotely executed (def update_job() is in this case called from remote.py's def put_job())
    if db_job.kaapana_instance.remote:
        db_job.status = job.status

    if (job.status == 'scheduled' and db_job.kaapana_instance.remote == False): #  or (job.status == 'failed'); status='scheduled' for restarting, status='failed' for aborting
        conf_data = json.loads(db_job.conf_data)
        conf_data['client_job_id'] = db_job.id
        dag_id_and_dataset = check_dag_id_and_dataset(db_job.kaapana_instance, conf_data, db_job.dag_id,
                                                      db_job.owner_kaapana_instance_name)
        if dag_id_and_dataset is not None:
            job.status = 'failed'
            job.description = dag_id_and_dataset
        else:
            airflow_execute_resp = execute_job_airflow(conf_data, db_job)
            airflow_execute_resp_text = json.loads(airflow_execute_resp.text)
            dag_id = airflow_execute_resp_text["message"][1]["dag_id"]
            dag_run_id = airflow_execute_resp_text["message"][1]["run_id"]
            db_job.dag_id = dag_id      # write directly to db_job to already use db_job.dag_id before db commit
            db_job.run_id = dag_run_id

    # check state and run_id for created or queued, scheduled, running jobs on local instance
    if db_job.run_id is not None and db_job.kaapana_instance.remote == False:
        # ask here first time Airflow for job status (explicit w/ job_id) via kaapana_api's def dag_run_status()
        airflow_details_resp = get_dagrun_details_airflow(db_job.dag_id, db_job.run_id)
        airflow_details_resp_text = json.loads(airflow_details_resp.text)
        # update db_job w/ job's real state and run_id fetched from Airflow
        db_job.status = "finished" if airflow_details_resp_text["state"] == "success" else airflow_details_resp_text["state"]  # special case for status = "success"
        db_job.run_id = airflow_details_resp_text["run_id"]

    if (db_job.kaapana_instance.remote != remote) and db_job.status not in ["queued", "finished", "failed"]:
        raise HTTPException(status_code=401,
                            detail="You are not allowed to update this job, since its on the client site")

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
    db_job = get_job(db, job.job_id)    # should actually be job.job_id instead of just job but somehow (unfortunately) works ...
    conf_data = json.loads(db_job.conf_data)
    conf_data['client_job_id'] = db_job.id

    # repsonse.text of abort_job_airflow usused in backend but might be valuable for debugging
    abort_job_airflow(db_job.dag_id, db_job.run_id, db_job.status, conf_data)

def get_job_taskinstances(db: Session, job_id: int = None):
    db_job = get_job(db, job_id)                                        # query job by job_id
    response = get_dagrun_tasks_airflow(db_job.dag_id, db_job.run_id)   # get task_instances w/ states via dag_id and run_id

    # parse received response
    response_text = json.loads(response.text)
    ti_state_dict = eval(response_text["message"][0])   # convert dict-like strings to dicts
    ti_exdate_dict = eval(response_text["message"][1])

    # compose dict in style {"task_instance": ["execution_time", "state"]}
    tis_n_state = {}
    for key in ti_state_dict:
        time_n_state = [ti_exdate_dict[key], ti_state_dict[key]]
        tis_n_state[key] = time_n_state

    return tis_n_state 


def sync_client_remote(db: Session, remote_kaapana_instance: schemas.RemoteKaapanaInstanceUpdateExternal,
                       instance_name: str = None, status: str = None):
    # logging.info(f"SYNC_CLIENT_REMOTE for instance_name: {instance_name} ; job status: {status}")
    db_client_kaapana = get_kaapana_instance(db, remote=False)

    create_and_update_remote_kaapana_instance(
        db=db, remote_kaapana_instance=remote_kaapana_instance, action='external_update')

    # get jobs on client_kaapana_instance with instance="instance_name" and status="status"
    db_outgoing_jobs = get_jobs(db, instance_name=instance_name, status=status, remote=True)
    outgoing_jobs = [schemas.Job(**job.__dict__).dict() for job in db_outgoing_jobs]
    logging.info(f"SYNC_CLIENT_REMOTE outgoing_jobs: {outgoing_jobs}")

    # get experiments on client_kaapana_instance which contain outgoing_jobs
    outgoing_experiments = []
    for db_outgoing_job in db_outgoing_jobs:
        db_outgoing_experiment = get_experiments(db, experiment_job_id=db_outgoing_job.id)
        outgoing_experiment = [schemas.Experiment(**experiment.__dict__).dict() for experiment in db_outgoing_experiment][0] if len(db_outgoing_experiment) > 0 else None
        outgoing_experiments.append(outgoing_experiment)
    logging.info(f"SYNC_CLIENT_REMOTE outgoing_experiments: {outgoing_experiments}")


    update_remote_instance_payload = {
        "instance_name": db_client_kaapana.instance_name,
        "allowed_dags": json.loads(db_client_kaapana.allowed_dags),
        "allowed_datasets": json.loads(db_client_kaapana.allowed_datasets),
        "automatic_update": db_client_kaapana.automatic_update,
        "automatic_job_execution": db_client_kaapana.automatic_job_execution
    }
    return {
        'incoming_jobs': outgoing_jobs,
        'incoming_experiments': outgoing_experiments,
        'update_remote_instance_payload': update_remote_instance_payload
    }


def delete_external_job(db: Session, db_job):
    if db_job.external_job_id is not None:
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
                logging.warning(f'External job {db_job.external_job_id} does not exist')
            else:
                raise_kaapana_connection_error(r)
                logging.error(r.json())


def update_external_job(db: Session, db_job):
    if db_job.external_job_id is not None:
        same_instance = db_job.owner_kaapana_instance_name == settings.instance_name

        db_remote_kaapana_instance = get_kaapana_instance(db, instance_name=db_job.owner_kaapana_instance_name,
                                                          remote=True)
        payload = {
            "job_id": db_job.external_job_id,
            "run_id": db_job.run_id,
            "status": db_job.status,
            "description": db_job.description
        }
        # update_job(db, schemas.JobUpdate(**payload))  # TRYOUT
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
                logging.warning(f'External job {db_job.external_job_id} does not exist')
            else:
                logging.error("Error in CRUD def update_external_job()")
                raise_kaapana_connection_error(r)
                logging.error(r.json())


def get_remote_updates(db: Session, periodically=False):
    db_client_kaapana = get_kaapana_instance(db, remote=False)
    if periodically is True and db_client_kaapana.automatic_update is False:
        return
    db_remote_kaapana_instances = get_kaapana_instances(db, filter_kaapana_instances=schemas.FilterKaapanaInstances(
        **{'remote': True}))
    # logging.info(f"GET REMOTE UPDATES FROM db_remote_kaapana_instances: {db_remote_kaapana_instances}")
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
            with requests.Session() as s:
                r = requests_retry_session(session=s).put(f'{remote_backend_url}/sync-client-remote', params=job_params,
                                                          json=update_remote_instance_payload,
                                                          verify=db_remote_kaapana_instance.ssl_check,
                                                          headers={
                                                              'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'},
                                                          timeout=TIMEOUT)
            if r.status_code == 405:
                logging.warning(f'Warning!!! We could not reach the following backend {db_remote_kaapana_instance.host}')
                continue
            raise_kaapana_connection_error(r)
            incoming_data = r.json()
        incoming_jobs = incoming_data['incoming_jobs']
        incoming_experiments = incoming_data['incoming_experiments']
        remote_kaapana_instance = schemas.RemoteKaapanaInstanceUpdateExternal(
            **incoming_data['update_remote_instance_payload'])

        create_and_update_remote_kaapana_instance(db=db, remote_kaapana_instance=remote_kaapana_instance,
                                                  action='external_update')

        # create experiment for incoming experiment if does NOT exist yet
        for incoming_experiment in incoming_experiments:
            # check if incoming_experiment already exists
            db_incoming_experiment = get_experiment(db, exp_id=incoming_experiment["exp_id"])
            # db_incoming_experiment = get_experiment(db, experiment_name=incoming_experiment['experiment_name']) # rather query via experiment_name than via exp_id
            if db_incoming_experiment is None:
                # if not: create incoming experiments
                incoming_experiment['kaapana_instance_id'] = db_remote_kaapana_instance.id
                # incoming_experiment['external_exp_id'] = incoming_experiment["id"]
                incoming_experiment['involved_kaapana_instances'] = incoming_experiment["involved_kaapana_instances"][1:-1].split(',')  # convert string "{node81_gpu, node82_gpu}" to list ['node81_gpu', 'node82_gpu']
                experiment = schemas.ExperimentCreate(**incoming_experiment)
                db_experiment = create_experiment(db, experiment)
                logging.info(f"Created incoming remote experiment: {db_experiment}")

        # create incoming jobs
        db_jobs = []
        for incoming_job in incoming_jobs:
            incoming_job['kaapana_instance_id'] = db_client_kaapana.id
            incoming_job['owner_kaapana_instance_name'] = db_remote_kaapana_instance.instance_name
            incoming_job['external_job_id'] = incoming_job["id"]
            incoming_job['status'] = "pending"
            job = schemas.JobCreate(**incoming_job)
            db_job = create_job(db, job)
            db_jobs.append(db_job)

        # update incoming experiments
        for incoming_experiment in incoming_experiments:
            exp_update = schemas.ExperimentUpdate(**{
                "exp_id": incoming_experiment["exp_id"],
                "experiment_name": incoming_experiment["experiment_name"],  # instead of db_incoming_experiment.experiment_name
                "experiment_jobs": db_jobs, #  instead of incoming_jobs
            })
            db_experiment = put_experiment_jobs(db, exp_update)
            logging.info(f"Updated remote experiment: {db_experiment}")


    return  # schemas.RemoteKaapanaInstanceUpdateExternal(**udpate_instance_payload)

def sync_states_from_airflow(db: Session, status: str = None, periodically=False):
    # get list from airflow for jobs in status=status: {'dag_run_id': 'state'} -> airflow_jobs_in_qsr_state
    airflow_jobs_in_state = get_dagruns_airflow(tuple([status]))
    # extract list of run_ids of jobs in qsr states
    airflow_jobs_runids = []
    for airflow_job in airflow_jobs_in_state:
        airflow_jobs_runids.append(airflow_job['run_id'])

    # get list from db with all db_jobs in status=status
    db_jobs_in_state = get_jobs(db, status=status)
    # extract list of dag_run_ids from db_jobs_in_qsr_state
    db_jobs_runids = []
    for db_job in db_jobs_in_state:
        db_jobs_runids.append(db_job.run_id)

    # find elements which are in current airflow_jobs_runids but not in db_jobs_runids from previous round
    diff_airflow_to_db = [elem for elem in airflow_jobs_runids if elem not in db_jobs_runids]
    # find elements which are in db_jobs_runids from previous round but not in current airflow_jobs_runids
    diff_db_to_airflow = [elem for elem in db_jobs_runids if elem not in airflow_jobs_runids]

    if len(diff_airflow_to_db) > 0:
        # request airflow for states of all jobs in diff_airflow_to_db && update db_jobs of all jobs in diff_airflow_to_db
        for diff_job_runid in diff_airflow_to_db:
            # get db_job from db via 'run_id'
            db_job = get_job(db, run_id=diff_job_runid) # fails for all airflow jobs which aren't user-created aka service-jobs
            if db_job is not None:
                # update db_job w/ updated state
                job_update = schemas.JobUpdate(**{
                        'job_id': db_job.id,
                        })
                update_job(db, job_update, remote=False)
    elif len(diff_db_to_airflow) > 0:
        # request airflow for states of all jobs in diff_db_to_airflow && update db_jobs of all jobs in diff_db_to_airflow
        for diff_job_runid in diff_db_to_airflow:
            if diff_job_runid is None:
                logging.info("Remote db_job --> created to be executed on remote instance!")
                pass
            # get db_job from db via 'run_id'
            db_job = get_job(db, run_id=diff_job_runid)
            # get runner kaapana instance of db_job
            if db_job is not None:
                # update db_job w/ updated state
                job_update = schemas.JobUpdate(**{
                        'job_id': db_job.id,
                        })
                update_job(db, job_update, remote=False)
    elif len(diff_airflow_to_db) == 0 and len(diff_db_to_airflow) == 0:
        pass    # airflow and db in sync :)
    else:
        logging.error("Error while syncing kaapana-backend with Airflow")

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
    '''
    Function to clean up unsuccessful synced jobs between airflow and backend.
    Function asks in backend for jobs in states 'queued', 'scheduled', 'running', asks Airflow for their real status and updates them.
    '''
    # get db_jobs in states "queued", "scheduled", "running"
    db_jobs_queued = get_jobs(db, status="queued")
    db_jobs_scheduled = get_jobs(db, status="scheduled")
    db_jobs_running = get_jobs(db, status="running")
    db_jobs_qsr = db_jobs_queued + db_jobs_scheduled + db_jobs_running

    # iterate over db_jobs_qsr
    for db_job in db_jobs_qsr:
        # call crud.update job fpr each db_job in list to sync it's state from airflow
        job_update = schemas.JobUpdate(**{
                        'job_id': db_job.id,
                        })
        update_job(db, job_update, remote=False)
        


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


def create_identifier_if_not_present(db, identifier: schemas.Identifier):
    db_identifier = get_identifier(db, identifier=identifier.identifier)

    if db_identifier:
        return db_identifier
    else:
        return create_identifier(db, identifier)


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
            create_identifier_if_not_present(db, schemas.Identifier(identifier=identifier))
            for identifier in get_uid_list_from_query(cohort.cohort_query)
        ]
    else:
        db_cohort_identifiers: List[models.Identifier] = [
            create_identifier_if_not_present(db, identifier)
            for identifier in cohort.cohort_identifiers
        ]

    logging.info('identifiers: ', db_cohort_identifiers)

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
    logging.info(username)
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

    logging.info(f'Updating cohort {cohort.cohort_name}')
    db_cohort = get_cohort(db, cohort.cohort_name)

    if cohort.cohort_name is not None:
        db_cohort.cohort_name = cohort.cohort_name

    if cohort.cohort_query and not cohort.cohort_identifiers:
        cohort.cohort_identifiers = get_uid_list_from_query(cohort.cohort_query)

    db_identifiers = [
        create_identifier_if_not_present(db, identifier)
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
    
    # if db.query(models.Experiment).filter_by(id=experiment.exp_id).first():            # experiment already exists?
    if get_experiment(db, exp_id=experiment.exp_id):
        raise HTTPException(status_code=409, detail="Experiment exists already!")  # ... raise http exception!
    if not db_kaapana_instance:                                                    # no kaapana_instance found in db in previous "search"?
        raise HTTPException(status_code=404, detail="Kaapana instance not found")  # ... raise http exception!
    
    utc_timestamp = get_utc_timestamp()

    db_experiment = models.Experiment(
        exp_id=experiment.exp_id,
        kaapana_id=experiment.kaapana_instance_id,
        username=experiment.username,
        experiment_name=experiment.experiment_name,
        experiment_jobs=experiment.experiment_jobs,                   # list experiment_jobs already added to experiment in client.py's def create_experiment()
        involved_kaapana_instances = experiment.involved_kaapana_instances,
        cohort_name=experiment.cohort_name,
        time_created=utc_timestamp,
        time_updated=utc_timestamp
    )

    # TODO: also update all involved_kaapana_instances with the exp_id in which they are involved

    db_kaapana_instance.experiments.append(db_experiment)
    db.add(db_kaapana_instance)
    db.commit()
    db.refresh(db_experiment)
    return db_experiment

# TODO removed async because our current database is not able to execute async methods
def queue_generate_jobs_and_add_to_exp(db: Session, db_client_kaapana: models.KaapanaInstance, db_experiment: models.Experiment, json_schema_data: schemas.JsonSchemaData, conf_data=None):
    # get variables
    single_execution = False    # initialize with False
    if "data_form" in conf_data and "cohort_name" in conf_data["data_form"]:
        data_form = conf_data["data_form"]
        single_execution = "workflow_form" in conf_data and "single_execution" in conf_data["workflow_form"] and conf_data["workflow_form"]["single_execution"] is True
        cohort_limit = int(data_form["cohort_limit"]) if ("cohort_limit" in data_form and data_form["cohort_limit"] is not None) else None
    username = conf_data["experiment_form"]["username"]

    # compose queued_jobs according to 'single_execution'
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
    
    # create jobs on conf_data["experiment_form"]["runner_instances"]
    db_jobs = []
    db_kaapana_instances = []
    for jobs_to_create in queued_jobs: 
        db_remote_kaapana_instances = get_kaapana_instances(db, filter_kaapana_instances=schemas.FilterKaapanaInstances(**{'remote': json_schema_data.remote, 
                'instance_names': conf_data["experiment_form"]["runner_instances"]
                }))
        # add client instance to instance list only if it is marked as an involved_instance of current experiment
        if db_client_kaapana.instance_name in conf_data['experiment_form']['runner_instances']:  # add client instance to instance list only if it is marked as an involved_instance of current experiment
            db_kaapana_instances.append(db_client_kaapana)
        db_kaapana_instances.extend(db_remote_kaapana_instances)
        db_kaapana_instances_set = set(db_kaapana_instances)

        for db_kaapana_instance in db_kaapana_instances_set:
            job = schemas.JobCreate(**{
                "status": "queued",
                "kaapana_instance_id": db_kaapana_instance.id,
                "owner_kaapana_instance_name": db_client_kaapana.instance_name,
                **jobs_to_create
            })

            db_job = create_job(db, job)
            db_jobs.append(db_job)

    # update experiment w/ created db_jobs
    experiment = schemas.ExperimentUpdate(**{
        "exp_id": db_experiment.exp_id,
        "experiment_name": db_experiment.experiment_name,
        "experiment_jobs": db_jobs,
    })
    put_experiment_jobs(db, experiment)

    return db_experiment


def get_experiment(db: Session, exp_id: str = None, experiment_name: str = None):
    if exp_id is not None:
        return db.query(models.Experiment).filter_by(exp_id=exp_id).first()
    elif experiment_name is not None:
        return db.query(models.Experiment).filter_by(experiment_name=experiment_name).first()
    # if not db_experiment:
    #     raise HTTPException(status_code=404, detail="Experiment not found")
    # return db_experiment

def get_experiments(db: Session, instance_name: str = None, involved_instance_name: str = None, experiment_job_id: int = None, limit=None):
    if instance_name is not None:
        return db.query(models.Experiment).join(models.Experiment.kaapana_instance, aliased=True).filter_by(instance_name=instance_name).order_by(desc(models.Experiment.time_updated)).limit(limit).all()
    elif involved_instance_name is not None:
        return db.query(models.Experiment).filter(models.Experiment.involved_kaapana_instances.contains(involved_instance_name)).all()
    elif experiment_job_id is not None:
        return db.query(models.Experiment).join(models.Experiment.experiment_jobs, aliased=True).filter_by(id=experiment_job_id).all()
    else:
        return db.query(models.Experiment).join(models.Experiment.kaapana_instance).order_by(desc(models.Experiment.time_updated)).limit(limit).all()   # , aliased=True

def update_experiment(db: Session, experiment=schemas.ExperimentUpdate):
    utc_timestamp = get_utc_timestamp()

    db_experiment = get_experiment(db, experiment.exp_id)

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

            # or update db_jobs on remote kaapana_instance
            elif db_experiment.kaapana_instance.remote is True and db_experiment.kaapana_instance.automatic_job_execution is True:    
                update_external_job(db, db_experiment_current_job)  # def update_external_job expects db_experiment_current_job of class models.Job

            else:
                raise HTTPException(status_code=404, detail="Job updating while updating the experiment failed!")

    db_experiment.time_updated = utc_timestamp
    db.commit()
    db.refresh(db_experiment)

    return db_experiment

def put_experiment_jobs(db: Session, experiment=schemas.ExperimentUpdate):
    utc_timestamp = get_utc_timestamp()

    print(f"CRUD def put_experiment_jobs() ExperimentUpdate experiment = {experiment}")

    # db_experiment = get_experiment(db, experiment_name=experiment.experiment_name)
    db_experiment = get_experiment(db, exp_id=experiment.exp_id)

    # get db_jobs via job_id which should be added to db_experiment
    db_jobs = []
    for experiment_job in experiment.experiment_jobs:
        if type(experiment_job) is dict:
            # experiment_job is a dict when call of def put_experiment_jobs() comes from backend
            db_job = get_job(db, experiment_job["id"]) 
        else:
            # experiment_job is no dict when call of def put_experiment_jobs() comes from KaapanaFederatedTraining
            db_job = get_job(db, experiment_job.id)      
        db_jobs.append(db_job)

    # add dat shit to dat experiment
    db_experiment.experiment_jobs.extend(db_jobs)
    # TODO: create set of db_experiment.experiment_jobs to avoid double listed jobs

    db_experiment.time_updated = utc_timestamp
    db.commit()
    db.refresh(db_experiment)


    return db_experiment


def delete_experiment(db: Session, exp_id: str):
    db_experiment = get_experiment(db, exp_id)   # get db's db_experiment object

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
