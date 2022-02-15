from ast import alias
import json
import uuid

from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, Request, HTTPException

from . import models, schemas
from app.utils import HOSTNAME, NODE_ID
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

def get_kaapana_instances(db: Session, remote: bool = True):
    return db.query(models.KaapanaInstance).filter_by(remote=remote).all()

def create_client_kaapana_instance(db: Session, client_kaapana_instance: schemas.ClientKaapanaInstanceCreate):

    db_client_kaapana_instance = get_kaapana_instance(db, remote=False)
    if db_client_kaapana_instance:
        delete_kaapana_instance(db, db_client_kaapana_instance.id)

    if client_kaapana_instance.fernet_encrypted is True:
        fernet_key=Fernet.generate_key().decode()
    else:
        fernet_key='deactivated'

    db_client_kaapana_instance = models.KaapanaInstance(
        node_id=NODE_ID,
        token=str(uuid.uuid4()),
        protocol='https',
        host=HOSTNAME,
        port=443,
        ssl_check=client_kaapana_instance.ssl_check,
        fernet_key=fernet_key,
        remote=False,
        allowed_dags=json.dumps(client_kaapana_instance.allowed_dags),
        allowed_datasets=json.dumps(client_kaapana_instance.allowed_datasets),
        automatic_update=client_kaapana_instance.automatic_update or False,
        automatic_job_execution=client_kaapana_instance.automatic_job_execution or False
    )

    db.add(db_client_kaapana_instance)
    db.commit()
    db.refresh(db_client_kaapana_instance)
    return db_client_kaapana_instance

def create_remote_kaapana_instance(db: Session, remote_kaapana_instance: schemas.RemoteKaapanaInstanceCreate):
    print(remote_kaapana_instance.node_id)
    db_remote_kaapana_instance = get_kaapana_instance(db, remote_kaapana_instance.node_id, remote=True)
    if db_remote_kaapana_instance:
        delete_kaapana_instance(db, db_remote_kaapana_instance.id)
    db_remote_kaapana_instance = models.KaapanaInstance(
            node_id=remote_kaapana_instance.node_id,
            token=remote_kaapana_instance.token,
            protocol='https',
            host=remote_kaapana_instance.host,
            port=remote_kaapana_instance.port,
            ssl_check=remote_kaapana_instance.ssl_check,
            fernet_key=remote_kaapana_instance.fernet_key or 'deactivated',
            remote=True,
        )

    db.add(db_remote_kaapana_instance)
    db.commit()
    db.refresh(db_remote_kaapana_instance)
    return db_remote_kaapana_instance

def create_job(db: Session, job: schemas.JobCreate):

    db_kaapana_instance = db.query(models.KaapanaInstance).filter_by(id=job.kaapana_instance_id).first()
    if not db_kaapana_instance:
        raise HTTPException(status_code=404, detail="Kaapana instance not found")

    print('db_kaapana_instance.automatic_job_execution')
    # if db_kaapana_instance.automatic_job_execution is True:
    #     status = 'pending'
    # else:
    #     status = 'scheduled'
    
    db_job = models.Job(
        conf_data=json.dumps(job.conf_data),
        remote_id=job.remote_id,
        dry_run=job.dry_run,
        status=job.status
    )

    db_kaapana_instance.jobs.append(db_job)
    db.add(db_kaapana_instance)
    db.commit()
    db.refresh(db_kaapana_instance)
    return db_job

def get_job(db: Session, job_id: int, remote: bool = True):
    db_job = db.query(models.Job).filter_by(id=job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job

def delete_job(db: Session, job_id: int, remote: bool = True):
    db_job = get_job(db, job_id, remote)
    if db_job.kaapana_instance.remote != remote:
        raise HTTPException(status_code=401, detail="You are not allowed to delete this job, since its on the client site")
    db.delete(db_job)
    db.commit()
    return {"ok": True}

def delete_jobs(db: Session):
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

def update_job(db: Session, job_id: int, status: str, remote: bool = True):
    db_job = get_job(db, job_id, remote)
    if db_job.kaapana_instance.remote != remote:
        raise HTTPException(status_code=401, detail="You are not allowed to update this job, since its on the client site")
    db_job.status = status
    db.commit()
    db.refresh(db_job)
    return db_job


