from asyncio import streams
from typing import Optional, List, Any
from sqlalchemy_json import NestedMutableDict, NestedMutableList
import json
import datetime
from pydantic import BaseModel, validator, root_validator


class KaapanaInstanceBase(BaseModel):
    ssl_check: bool
    automatic_update: bool = False
    automatic_workflow_execution: bool = False


class ClientKaapanaInstanceCreate(KaapanaInstanceBase):
    fernet_encrypted: bool
    allowed_dags: list = []
    allowed_datasets: list = []


class RemoteKaapanaInstanceCreate(KaapanaInstanceBase):
    token: str
    host: str
    instance_name: str
    port: int
    fernet_key: str = "deactivated"
    allowed_dags: list = []
    allowed_datasets: list = []


class RemoteKaapanaInstanceUpdateExternal(BaseModel):
    instance_name: str
    allowed_dags: dict
    allowed_datasets: list
    automatic_update: bool = False
    automatic_workflow_execution: bool = False


class KaapanaInstance(KaapanaInstanceBase):
    id: int
    token: str
    protocol: str
    host: str
    instance_name: str
    port: int
    fernet_key: str
    encryption_key: str
    remote: bool
    allowed_dags: Optional[NestedMutableDict] = ...
    allowed_datasets: Optional[NestedMutableList] = ...
    time_created: datetime.datetime
    time_updated: datetime.datetime
    workflow_in_which_involved: Optional[str]

    @validator("allowed_dags")
    def convert_allowed_dags(cls, v):
        return sorted(v)

    @validator("time_created")
    def convert_time_created(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)

    @validator("time_updated")
    def convert_time_updated(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)

    @classmethod
    def clean_return(cls, instance):
        instance.encryption_key = ""
        return instance

    @classmethod
    def clean_full_return(cls, instance):
        instance.encryption_key = ""
        instance.fernet_key = ""
        instance.token = ""
        return instance

    class Config:
        orm_mode = True


class JobBase(BaseModel):
    status: str = "pending"
    dag_id: str = None
    run_id: str = None
    description: str = None
    external_job_id: int = None  # job_id on another system
    # kaapana_instance_id: int
    owner_kaapana_instance_name: str = (
        None  # Remote Kaapana instance that is addressed, not external kaapana_instance_id!
    )
    service_job: Optional[bool] = False


class Job(JobBase):
    id: int
    conf_data: Optional[NestedMutableDict] = ...
    username: str = None
    time_created: datetime.datetime
    time_updated: datetime.datetime

    @validator("status")
    def check_status(cls, v):
        allowed_states = [
            "queued",
            "pending",
            "scheduled",
            "running",
            "finished",
            "failed",
            "deleted",
        ]
        if v not in allowed_states:
            raise ValueError(
                f'status must be on of the following values: {", ".join(allowed_states)}'
            )
        return v

    @validator("time_created")
    def convert_time_created(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)

    @validator("time_updated")
    def convert_time_updated(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)

    class Config:
        orm_mode = True


class JobCreate(JobBase):
    conf_data: dict = {}
    kaapana_instance_id: int
    # workflow_id: int = None
    username: str = None
    automatic_execution: Optional[bool] = False


class JobUpdate(JobBase):
    job_id: (
        int  # not defined in model Workflow but still needed in client.py and crud.py
    )
    # status: str
    # run_id: str = None
    # description: str = None


class JobWithKaapanaInstance(Job):
    kaapana_instance: KaapanaInstance = None


class KaapanaInstanceWithJobs(KaapanaInstance):
    jobs: List[Job] = []


class FilterKaapanaInstances(BaseModel):
    federated: bool = False
    dag_id: str = None
    instance_names: List = []
    workflow_id: str = None
    workflow_name: str = None
    only_dag_names: bool = True
    kind_of_dags: str = None


class JsonSchemaData(FilterKaapanaInstances):
    conf_data: dict = {}
    username: str = None


class DatasetBase(BaseModel):
    name: str = None


class DatasetCreate(DatasetBase):
    kaapana_instance_id: int = None
    username: str = None
    identifiers: List[str] = []


class DatasetUpdate(DatasetBase):
    action: str = ""
    identifiers: List[str] = []


class Dataset(DatasetBase):
    time_created: datetime.datetime
    time_updated: datetime.datetime
    username: str = None
    identifiers: Optional[List[str]]

    @validator("time_updated")
    def convert_time_updated(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)

    class Config:
        orm_mode = True


class AllowedDatasetCreate(DatasetBase):
    username: str = None
    identifiers: Optional[List[str]]

    class Config:
        orm_mode = True


class WorkflowBase(BaseModel):
    workflow_id: str = None
    workflow_name: str = None
    workflow_status: str = None
    # external_workflow_id: int = None # workflow_id on another system
    # dag_id of jobs which are summarized in that workflow (only makes sense for service workflows)
    dag_id: Optional[str] = None
    service_workflow: Optional[bool] = False
    federated: bool = False


class Workflow(WorkflowBase):
    username: str = None
    status: str = None
    time_created: datetime.datetime = None
    time_updated: datetime.datetime = None
    automatic_execution: Optional[bool] = False
    involved_kaapana_instances: str = None  # List = []

    @validator("time_created")
    def convert_time_created(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)

    @validator("time_updated")
    def convert_time_updated(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)

    class Config:  # makes Pydantic model compatible with sqlalchemy ORMs
        orm_mode = True


class WorkflowCreate(WorkflowBase):
    username: str = None
    kaapana_instance_id: int
    workflow_jobs: List = []  # List[Job] = []
    involved_kaapana_instances: list = []


class WorkflowUpdate(WorkflowBase):
    workflow_name: Optional[str] = None  # ... or workflow_name
    workflow_jobs: List = []


class WorkflowWithKaapanaInstance(Workflow):
    kaapana_instance: KaapanaInstance = None
    # involved_kaapana_instances: list = []


class KaapanaInstanceWithWorkflows(KaapanaInstance):
    workflows: List[Workflow] = []


class JobWithWorkflow(Job):
    workflow: Workflow = None
    # involved_kaapana_instances: Optional[list]  # idk y?


class JobWithWorkflowWithKaapanaInstance(JobWithKaapanaInstance):
    workflow: Workflow = None


class WorkflowWithJobs(Workflow):
    jobs: List[Job] = []


class WorkflowWithKaapanaInstanceWithJobs(WorkflowWithKaapanaInstance):
    # workflow_jobs: List[Job] = []
    workflow_jobs: Optional[List]
    dataset_name: Optional[str]

    @root_validator
    def get_dataset(cls, values) -> str:
        # method to conclude from dataset of workflow_jobs the dataset of the workflow
        db_workflow_jobs = values.get("workflow_jobs", [])
        for job in db_workflow_jobs:
            if "external_schema_federated_form" in job.conf_data:
                # if workflow is a federated workflow, retrieve dataset_name from next job of workflow_jobs
                continue
            if "data_form" in job.conf_data and job.service_job == False:
                dataset_name = (
                    job.conf_data["data_form"]["dataset_name"]
                    if "dataset_name" in job.conf_data["data_form"]
                    else None
                )
                values["dataset_name"] = dataset_name
                # after getting the dataset_name from a workflow_job, break the for loop
                break
        return values

    @root_validator
    def get_workflow_jobs(cls, values) -> List:
        # method to only list workflow_jobs' states in workflow_jobs and not whole Job object
        workflow_job_states = []
        db_workflow_jobs = values.get("workflow_jobs", [])
        for db_job in db_workflow_jobs:
            if type(db_job) is not str:
                workflow_job_states.append(db_job.status)
        values["workflow_jobs"] = workflow_job_states
        return values
