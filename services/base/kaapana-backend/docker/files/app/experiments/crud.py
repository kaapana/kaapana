from ast import alias
import json
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
from .utils import get_dataset_list, execute_job, check_dag_id_and_dataset, get_utc_timestamp, HelperMinio, get_dag_list, raise_kaapana_connection_error
from urllib.parse import urlparse


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
    return db.query(models.KaapanaInstance).filter_by(instance_name=instance_name or settings.instance_name, remote=remote).first()

def get_kaapana_instances(db: Session, filter_kaapana_instances: schemas.FilterKaapanaInstances = None):
    if filter_kaapana_instances.instance_names:
        return db.query(models.KaapanaInstance).filter(models.KaapanaInstance.remote==filter_kaapana_instances.remote, models.KaapanaInstance.instance_name.in_(filter_kaapana_instances.instance_names)).all()
    elif filter_kaapana_instances.dag_id is not None:
        return db.query(models.KaapanaInstance).filter(models.KaapanaInstance.remote==filter_kaapana_instances.remote, models.KaapanaInstance.allowed_dags.contains(filter_kaapana_instances.dag_id)).all()
    elif filter_kaapana_instances.instance_names and filter_kaapana_instances.dag_id is not None:
        return db.query(models.KaapanaInstance).filter(models.KaapanaInstance.remote==filter_kaapana_instances.remote, models.KaapanaInstance.allowed_dags.contains(filter_kaapana_instances.dag_id), models.KaapanaInstance.instance_name.in_(filter_kaapana_instances.instance_names)).all()
    else:
        return db.query(models.KaapanaInstance).filter_by(remote=filter_kaapana_instances.remote).all()

def create_and_update_client_kaapana_instance(db: Session, client_kaapana_instance: schemas.ClientKaapanaInstanceCreate, action='create'):
    def _get_fernet_key(fernet_encrypted):
        if fernet_encrypted is True:
            return Fernet.generate_key().decode()
        else:
            return 'deactivated'
    utc_timestamp = get_utc_timestamp()
    allowed_dags = json.dumps(get_dag_list(only_dag_names=False, filter_allowed_dags=client_kaapana_instance.allowed_dags))
    allowed_datasets = json.dumps([dataset for dataset in client_kaapana_instance.allowed_datasets if dataset in get_dataset_list(unique_sets=True)])
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
    elif action=='update':
        if db_client_kaapana_instance.fernet_key == 'deactivated' and client_kaapana_instance.fernet_encrypted is True:
            db_client_kaapana_instance.fernet_key=_get_fernet_key(client_kaapana_instance.fernet_encrypted)
        elif  db_client_kaapana_instance.fernet_key != 'deactivated' and client_kaapana_instance.fernet_encrypted is False:
            db_client_kaapana_instance.fernet_key = 'deactivated'
        db_client_kaapana_instance.ssl_check=client_kaapana_instance.ssl_check
        db_client_kaapana_instance.allowed_dags=allowed_dags
        db_client_kaapana_instance.allowed_datasets=allowed_datasets
        db_client_kaapana_instance.automatic_update=client_kaapana_instance.automatic_update or False
        db_client_kaapana_instance.automatic_job_execution=client_kaapana_instance.automatic_job_execution or False
    else:
        raise NameError('action must be one of create, update')

    db.add(db_client_kaapana_instance)
    db.commit()
    db.refresh(db_client_kaapana_instance)
    return db_client_kaapana_instance

def create_and_update_remote_kaapana_instance(db: Session, remote_kaapana_instance: schemas.RemoteKaapanaInstanceCreate, action='create'):
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
    elif action=='update':
        db_remote_kaapana_instance.token=remote_kaapana_instance.token
        db_remote_kaapana_instance.port=remote_kaapana_instance.port
        db_remote_kaapana_instance.ssl_check=remote_kaapana_instance.ssl_check
        db_remote_kaapana_instance.fernet_key=remote_kaapana_instance.fernet_key or 'deactivated'
        db_remote_kaapana_instance.time_updated=utc_timestamp
    elif action=='external_update':
        if db_remote_kaapana_instance:
            db_remote_kaapana_instance.allowed_dags = json.dumps(remote_kaapana_instance.allowed_dags)
            db_remote_kaapana_instance.allowed_datasets = json.dumps(remote_kaapana_instance.allowed_datasets)
            db_remote_kaapana_instance.automatic_update=remote_kaapana_instance.automatic_update or False
            db_remote_kaapana_instance.automatic_job_execution=remote_kaapana_instance.automatic_job_execution or False
            db_remote_kaapana_instance.time_updated=utc_timestamp
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

    db_job = models.Job(
        conf_data=json.dumps(job.conf_data),
        time_created=utc_timestamp,
        time_updated=utc_timestamp,
        external_job_id=job.external_job_id,
        dag_id=job.dag_id,
        addressed_kaapana_instance_name=job.addressed_kaapana_instance_name, # or None,
        status=job.status
    )

    db_kaapana_instance.jobs.append(db_job)
    db.add(db_kaapana_instance)
    try:
        db.commit() # writing, if kaapana_id and external_job_id already exists will fail due to duplicate error
    except IntegrityError as e:
            assert isinstance(e.orig, UniqueViolation)  # proves the original exception
            return db.query(models.Job).filter_by(external_job_id=db_job.external_job_id, addressed_kaapana_instance_name=db_job.addressed_kaapana_instance_name).first()
    
    update_external_job(db, db_job)
    db.refresh(db_job)
    if db_kaapana_instance.remote is False and db_kaapana_instance.automatic_job_execution is True:
        job = schemas.JobUpdate(**{
            'job_id': db_job.id,
            'status': 'scheduled',
            'description':'The worklow was triggered!'
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
    if (db_job.kaapana_instance.remote != remote) and db_job.status not in ["queued", "finished", "failed"]:
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
        return db.query(models.Job).filter_by(status=status).join(models.Job.kaapana_instance, aliased=True).filter_by(instance_name=instance_name, remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()
    elif instance_name is not None:
        return db.query(models.Job).join(models.Job.kaapana_instance, aliased=True).filter_by(instance_name=instance_name, remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()
    elif status is not None:
        return db.query(models.Job).filter_by(status=status).join(models.Job.kaapana_instance, aliased=True).filter_by(remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()
    else:
        return db.query(models.Job).join(models.Job.kaapana_instance, aliased=True).filter_by(remote=remote).order_by(desc(models.Job.time_updated)).limit(limit).all()

def update_job(db: Session, job=schemas.JobUpdate, remote: bool = True):
    utc_timestamp = get_utc_timestamp()

    print(f'Updating client job {job.job_id}')
    db_job = get_job(db, job.job_id)

    if job.status == 'scheduled' and db_job.kaapana_instance.remote == False:
        print(f'Executing  job {db_job.id}')
        conf_data = json.loads(db_job.conf_data)
        conf_data['client_job_id'] = db_job.id
        dag_id_and_dataset = check_dag_id_and_dataset(db_job.kaapana_instance, conf_data, db_job.dag_id, db_job.addressed_kaapana_instance_name) 
        if dag_id_and_dataset is not None:
            job.status = 'failed'
            job.description = dag_id_and_dataset
        else:
            execute_job(conf_data, db_job.dag_id)

    if (db_job.kaapana_instance.remote != remote) and db_job.status not in ["queued", "finished", "failed"]:
        raise HTTPException(status_code=401, detail="You are not allowed to update this job, since its on the client site")
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

def sync_client_remote(db: Session,  remote_kaapana_instance: schemas.RemoteKaapanaInstanceUpdateExternal, instance_name: str = None, status: str = None):
    db_client_kaapana = get_kaapana_instance(db, remote=False)

    create_and_update_remote_kaapana_instance(
        db=db, remote_kaapana_instance=remote_kaapana_instance, action='external_update')
    db_incoming_jobs = get_jobs(db, instance_name=instance_name, status=status, remote=True)
    incoming_jobs = [schemas.Job(**job.__dict__).dict() for job in db_incoming_jobs]

    update_remote_instance_payload = {
        "instance_name":  db_client_kaapana.instance_name,
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
        print(f'Deleting remote job {db_job.external_job_id}, {db_job.addressed_kaapana_instance_name}')
        same_instance = db_job.addressed_kaapana_instance_name == settings.instance_name
        db_remote_kaapana_instance = get_kaapana_instance(db, instance_name=db_job.addressed_kaapana_instance_name, remote=True)
        params = {
            "job_id": db_job.external_job_id,
        }
        if same_instance:
            delete_job(db, **params)
        else:
            remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/kaapana-backend/remote'
            with requests.Session() as s:          
                r = requests_retry_session(session=s).delete(f'{remote_backend_url}/job', verify=db_remote_kaapana_instance.ssl_check, params=params, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
            if r.status_code == 404:
                print(f'External job {db_job.external_job_id} does not exist')
            else:
                raise_kaapana_connection_error(r)
                print(r.json())

def update_external_job(db: Session, db_job):
    if db_job.external_job_id is not None:
        print(f'Updating remote job {db_job.external_job_id}, {db_job.addressed_kaapana_instance_name}')
        same_instance = db_job.addressed_kaapana_instance_name == settings.instance_name
        db_remote_kaapana_instance = get_kaapana_instance(db, instance_name=db_job.addressed_kaapana_instance_name, remote=True)
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
                r = requests_retry_session(session=s).put(f'{remote_backend_url}/job', verify=db_remote_kaapana_instance.ssl_check, json=payload, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
            if r.status_code == 404:
                print(f'External job {db_job.external_job_id} does not exist')
            else:
                raise_kaapana_connection_error(r)
                print(r.json())


def get_remote_updates(db: Session, periodically=False):
    db_client_kaapana = get_kaapana_instance(db, remote=False)
    if periodically is True and db_client_kaapana.automatic_update is False:
        return
    db_remote_kaapana_instances = get_kaapana_instances(db, filter_kaapana_instances=schemas.FilterKaapanaInstances(**{'remote': True}))
    for db_remote_kaapana_instance in db_remote_kaapana_instances:
        same_instance = db_remote_kaapana_instance.instance_name == settings.instance_name
        update_remote_instance_payload = {
            "instance_name":  db_client_kaapana.instance_name,
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
            incoming_data = sync_client_remote(db=db, remote_kaapana_instance=schemas.RemoteKaapanaInstanceUpdateExternal(**update_remote_instance_payload), **job_params)
        else:
            remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/kaapana-backend/remote'
            with requests.Session() as s:     
                r = requests_retry_session(session=s).put(f'{remote_backend_url}/sync-client-remote', params=job_params,  json=update_remote_instance_payload, verify=db_remote_kaapana_instance.ssl_check, 
            headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
            if r.status_code == 405:
                print(f'Warning!!! We could not reach the following backend {db_remote_kaapana_instance.host}')
                continue
            raise_kaapana_connection_error(r)
            incoming_data =  r.json()
        incoming_jobs = incoming_data['incoming_jobs']
        remote_kaapana_instance = schemas.RemoteKaapanaInstanceUpdateExternal(**incoming_data['update_remote_instance_payload'])

        create_and_update_remote_kaapana_instance(db=db, remote_kaapana_instance=remote_kaapana_instance, action='external_update')

        for incoming_job in incoming_jobs:
            print('Creating', incoming_job["id"])
            incoming_job['kaapana_instance_id'] = db_client_kaapana.id
            incoming_job['addressed_kaapana_instance_name'] = db_remote_kaapana_instance.instance_name
            incoming_job['external_job_id'] = incoming_job["id"]
            incoming_job['status'] = "pending"
            job = schemas.JobCreate(**incoming_job)
            db_job = create_job(db, job)

    return #schemas.RemoteKaapanaInstanceUpdateExternal(**udpate_instance_payload)
