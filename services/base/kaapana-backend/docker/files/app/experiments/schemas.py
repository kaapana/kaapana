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
    instance_name: str
    port: int
    fernet_key: str = 'deactivated'
    allowed_dags: list = []
    allowed_datasets: list = []


class RemoteKaapanaInstanceUpdateExternal(BaseModel):
    instance_name: str
    allowed_dags: dict
    allowed_datasets: list
    automatic_update: bool = False
    automatic_job_execution: bool = False


class KaapanaInstance(KaapanaInstanceBase):
    id: int
    token: str
    protocol: str
    host: str
    instance_name: str
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

    @validator('time_created')
    def convert_time_created(cls, v):
        return datetime.datetime.timestamp(v)

    @validator('time_updated')
    def convert_time_updated(cls, v):
        return datetime.datetime.timestamp(v)

    class Config:
        orm_mode = True


class JobBase(BaseModel):
    status: str = 'pending'
    dag_id: str = None
    run_id: str = None
    description: str = None
    external_job_id: int = None  # job_id on another system
    addressed_kaapana_instance_name: str = None  # Remote Kaapana instance that is addressed, not external kaapana_instance_id!


class Job(JobBase):
    id: int
    conf_data: str
    username: str = None
    time_created: datetime.datetime
    time_updated: datetime.datetime

    @validator('status')
    def check_status(cls, v):
        allowed_states = ['queued', 'pending', 'scheduled', 'running', 'finished', 'failed']
        if v not in allowed_states:
            raise ValueError(f'status must be on of the following values: {", ".join(allowed_states)}')
        return v

    @validator('conf_data')
    def convert_conf_data(cls, v):
        return json.loads(v)

    class Config:
        orm_mode = True


class JobCreate(JobBase):
    conf_data: dict = {}
    kaapana_instance_id: int
    username: str = None


class JobUpdate(JobBase):
    job_id: int
    # status: str
    # run_id: str = None
    # description: str = None


class JobWithKaapanaInstance(Job):
    kaapana_instance: KaapanaInstance = None


class KaapanaInstanceWithJobs(KaapanaInstance):
    jobs: List[Job] = []


class FilterKaapanaInstances(BaseModel):
    remote: bool = True
    dag_id: str = None
    instance_names: List = []


class JsonSchemaData(FilterKaapanaInstances):
    conf_data: dict = {}
    username: str = None


class Identifier(BaseModel):
    identifier: str = None

    class Config:
        orm_mode = True


class CohortBase(BaseModel):
    cohort_name: str = None


class CohortCreate(CohortBase):
    cohort_query: dict = {}
    cohort_identifiers: List[Identifier] = []
    kaapana_instance_id: int = None
    username: str = None


class CohortUpdate(CohortBase):
    action: str = ""
    cohort_query: dict = {}
    cohort_identifiers: List[Identifier] = []


class Cohort(CohortBase):
    cohort_query: str
    cohort_identifiers: List[Identifier]
    time_created: datetime.datetime
    time_updated: datetime.datetime
    username: str = None

    @validator('cohort_query')
    def convert_cohort_query(cls, v):
        return json.loads(v)

    # @validator('cohort_identifiers')
    # def convert_cohort_identifiers(cls, v):
    #     return json.loads(v)

    @validator('time_created')
    def convert_time_created(cls, v):
        return datetime.datetime.timestamp(v)

    @validator('time_updated')
    def convert_time_updated(cls, v):
        return datetime.datetime.timestamp(v)

    class Config:
        orm_mode = True
