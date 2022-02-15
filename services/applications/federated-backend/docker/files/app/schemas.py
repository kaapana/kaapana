from asyncio import streams
from typing import Optional, List
import json
from pydantic import BaseModel, validator


class KaapanaInstanceBase(BaseModel):
    ssl_check: bool
    automatic_update: bool = False
    automatic_job_execution: bool = False


class ClientKaapanaInstanceCreate(KaapanaInstanceBase):
    fernet_encrypted: bool
    allowed_dags: list
    allowed_datasets: list


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
    
    @validator('allowed_dags')
    def convert_allowed_dags(cls, v):
        return json.loads(v)

    @validator('allowed_datasets')
    def convert_allowed_datasets(cls, v):
        return json.loads(v)

    class Config:
        orm_mode = True


class RemoteKaapanaInstanceCreate(KaapanaInstanceBase):
    token: str
    host: str
    node_id: str
    port: int
    fernet_key: str = 'deactivated'
    allowed_dags: list = []
    allowed_datasets: list = []
    

class JobBase(BaseModel):
    dry_run: bool = False
    remote_id: int = None
    status: str = 'pending'

class Job(JobBase):
    id: int

    conf_data: str


    @validator('status')
    def check_status(cls, v):
        allowed_states =  ['queued', 'pending', 'scheduled', 'running', 'finished']
        if v not in allowed_states:
            raise ValueError(f'status must be on of the following values: {", ".join(allowed_states)}')
        return v

    @validator('conf_data')
    def convert_conf_Data(cls, v):
        return json.loads(v)

    class Config:
        orm_mode = True

class JobCreate(JobBase):
    conf_data: dict = {}
    kaapana_instance_id: int


class JobWithKaapanaInstance(Job):
    kaapana_instances: List[KaapanaInstance] = []


class KaapanaInstanceWithJob(KaapanaInstance):
    jobs: List[Job] = []

