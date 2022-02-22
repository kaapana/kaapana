from asyncio import streams
from typing import Optional, List
import json
import datetime
from pydantic import BaseModel, validator


class KaapanaInstanceBase(BaseModel):
    ssl_check: bool
    automatic_update: bool = False
    automatic_job_execution: bool = False

class ClientKaapanaInstanceCreate(KaapanaInstanceBase):
    fernet_encrypted: bool
    allowed_dags: list
    allowed_datasets: list

class RemoteKaapanaInstanceCreate(KaapanaInstanceBase):
    token: str
    host: str
    node_id: str
    port: int
    fernet_key: str = 'deactivated'
    allowed_dags: list = []
    allowed_datasets: list = []

class RemoteKaapanaInstanceUpdateExternal(BaseModel):
    node_id: str
    allowed_dags: dict
    allowed_datasets: list
    automatic_update: bool = False
    automatic_job_execution: bool = False

class KaapanaInstance(KaapanaInstanceBase):
    id: int
    token: str
    protocol: str
    host: str
    node_id: str
    port: int
    fernet_key: str
    remote: bool
    allowed_dags: str
    allowed_datasets: str
    time_created: datetime.datetime
    time_updated: datetime.datetime
    
    @validator('allowed_dags')
    def convert_allowed_dags(cls, v):
        return sorted(json.loads(v))
        # print(sorted(json.loads(v).keys()))
        return sorted(json.loads(v).keys())

    @validator('allowed_datasets')
    def convert_allowed_datasets(cls, v):
        return json.loads(v)

    class Config:
        orm_mode = True


class JobBase(BaseModel):
    dry_run: bool = False
    status: str = 'pending'
    run_id: str = None
    description: str = None
    external_job_id: int = None # job_id on another system
    addressed_kaapana_node_id: str = None # Remote Kaapana instance that is addressed, not external kaapana_instance_id!


class Job(JobBase):
    id: int
    conf_data: str
    job_data: str
    time_created: datetime.datetime
    time_updated: datetime.datetime

    @validator('status')
    def check_status(cls, v):
        allowed_states =  ['queued', 'pending', 'scheduled', 'running', 'finished', 'failed']
        if v not in allowed_states:
            raise ValueError(f'status must be on of the following values: {", ".join(allowed_states)}')
        return v

    @validator('conf_data')
    def convert_conf_data(cls, v):
        return json.loads(v)

    @validator('job_data')
    def convert_job_data(cls, v):
        return json.loads(v)

    class Config:
        orm_mode = True


class JobCreate(JobBase):
    conf_data: dict = {}
    job_data: dict = {}
    local_data: dict = {}
    kaapana_instance_id: int

class JobUpdate(JobBase):
    job_id: int
    # status: str
    # run_id: str = None
    # description: str = None


class JobWithKaapanaInstance(Job):
    kaapana_instance: KaapanaInstance = None

class KaapanaInstanceWithJobs(KaapanaInstance):
    jobs: List[Job] = []

class FilterByNodeIds(BaseModel):
    node_ids: List = []
