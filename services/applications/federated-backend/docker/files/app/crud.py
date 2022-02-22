from ast import alias
import json
from urllib import request
import uuid
import requests


from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, Request, HTTPException, Response

from . import models, schemas
from app.utils import HOSTNAME, NODE_ID, update_external_job, delete_external_job, execute_job, get_utc_timestamp, HelperMinio, get_dag_list, raise_kaapana_connection_error
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

def get_kaapana_instance(db: Session, node_id: str = None, remote: bool = True):
    return db.query(models.KaapanaInstance).filter_by(node_id=node_id or NODE_ID, remote=remote).first()

def get_kaapana_instances(db: Session, remote: bool = True, filter_by_node_ids: schemas.FilterByNodeIds = None):
    if filter_by_node_ids is not None:
        return db.query(models.KaapanaInstance).filter(models.KaapanaInstance.remote==remote, models.KaapanaInstance.node_id.in_(filter_by_node_ids.node_ids)).all()
    else:
        return db.query(models.KaapanaInstance).filter_by(remote=remote).all()

def create_and_update_client_kaapana_instance(db: Session, client_kaapana_instance: schemas.ClientKaapanaInstanceCreate, action='create'):
    def _get_fernet_key(fernet_encrypted):
        if fernet_encrypted is True:
            return Fernet.generate_key().decode()
        else:
            return 'deactivated'
    utc_timestamp = get_utc_timestamp()
    allowed_dags = json.dumps(get_dag_list(only_dag_names=False, filter_allowed_dags=client_kaapana_instance.allowed_dags))
    print(allowed_dags)
    db_client_kaapana_instance = get_kaapana_instance(db, remote=False)
    if action == 'create':
        if db_client_kaapana_instance:
            raise HTTPException(status_code=400, detail="Kaapana instance already exists!")

    if action == 'create':
        db_client_kaapana_instance = models.KaapanaInstance(
            node_id=NODE_ID,
            token=str(uuid.uuid4()),
            protocol='https',
            host=HOSTNAME,
            port=443,
            ssl_check=client_kaapana_instance.ssl_check,
            fernet_key=_get_fernet_key(client_kaapana_instance.fernet_encrypted),
            remote=False,
            allowed_dags=allowed_dags,
            allowed_datasets=json.dumps(client_kaapana_instance.allowed_datasets),
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
        db_client_kaapana_instance.allowed_datasets=json.dumps(client_kaapana_instance.allowed_datasets)
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
    db_remote_kaapana_instance = get_kaapana_instance(db, remote_kaapana_instance.node_id, remote=True)
    if action == 'create':
        if db_remote_kaapana_instance:
            raise HTTPException(status_code=400, detail="Kaapana instance already exists!")
    if action == 'create':
        db_remote_kaapana_instance = models.KaapanaInstance(
                node_id=remote_kaapana_instance.node_id,
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
            return Response("Your node id differs from the remote node id!", 200)
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

    if db_kaapana_instance.remote is True and 'federated' in job.local_data and 'federated' in job.job_data:
        minio_urls = HelperMinio.add_minio_urls(
            job.job_data['federated'],
            job.local_data['federated'],
            db_kaapana_instance.node_id
        )
        job.job_data['federated']['minio_urls'] = minio_urls

    print('db_kaapana_instance.automatic_job_execution')
    # if db_kaapana_instance.automatic_job_execution is True:
    #     status = 'pending'
    # else:
    #     status = 'scheduled'
    
    utc_timestamp = get_utc_timestamp()

    db_job = models.Job(
        conf_data=json.dumps(job.conf_data),
        job_data=json.dumps(job.job_data),
        local_data=json.dumps(job.local_data),
        time_created=utc_timestamp,
        time_updated=utc_timestamp,
        external_job_id=job.external_job_id,
        addressed_kaapana_node_id=job.addressed_kaapana_node_id or None,
        dry_run=job.dry_run,
        status=job.status
    )

    db_kaapana_instance.jobs.append(db_job)
    db.add(db_kaapana_instance)
    db.commit()
    update_external_job(db, db_job)
    db.refresh(db_kaapana_instance)
    return db_job

def get_job(db: Session, job_id: int):
    db_job = db.query(models.Job).filter_by(id=job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job

def delete_job(db: Session, job_id: int, remote: bool = True):
    db_job = get_job(db, job_id)
    if (db_job.kaapana_instance.remote != remote) and db_job.status not in ["queued", "scheduled", "finished", "failed"]:
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

def get_jobs(db: Session, node_id: str = None, status: str = None, remote: bool = True):
    if node_id is not None and status is not None:
        return db.query(models.Job).filter_by(status=status).join(models.Job.kaapana_instance, aliased=True).filter_by(node_id=node_id, remote=remote).all()
    elif node_id is not None:
        return db.query(models.Job).join(models.Job.kaapana_instance, aliased=True).filter_by(node_id=node_id, remote=remote).all()
    elif status is not None:
        return db.query(models.Job).filter_by(status=status).join(models.Job.kaapana_instance, aliased=True).filter_by(remote=remote).all()
    else:
        return db.query(models.Job).join(models.Job.kaapana_instance, aliased=True).filter_by(remote=remote).all()

def update_job(db: Session, job=schemas.JobUpdate, remote: bool = True):
    utc_timestamp = get_utc_timestamp()

    print(f'Updating client job {job.job_id}')
    db_job = get_job(db, job.job_id)

    if job.status == 'running' and db_job.status != 'running' and db_job.kaapana_instance.remote == False:
        print(f'Executing  job {db_job.id}')
        execute_job(db_job)

    if (db_job.kaapana_instance.remote != remote) and db_job.status not in ["queued", "scheduled", "finished", "failed"]:
        raise HTTPException(status_code=401, detail="You are not allowed to update this job, since its on the client site")
    db_job.status = job.status
    if job.run_id is not None:
        db_job.run_id = job.run_id
    if job.description is not None:
        db_job.description = job.description
    db_job.time_updated = utc_timestamp
    db.commit()
    db.refresh(db_job)

    update_external_job(db, db_job)

    return db_job


