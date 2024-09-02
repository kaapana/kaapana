import datetime
from typing import Any, List, Optional, Union

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlalchemy_json import NestedMutableDict, NestedMutableList
from typing_extensions import Self


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
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
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

    @field_validator("allowed_dags", mode="after")
    @classmethod
    def convert_allowed_dags(cls, v):
        return sorted(v)

    @field_validator("time_created", mode="before")
    @classmethod
    def convert_time_created(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)

    @field_validator("time_updated", mode="before")
    @classmethod
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


class JobBase(BaseModel):
    status: str = "pending"
    dag_id: Optional[str] = None
    run_id: Optional[str] = None
    description: Optional[str] = None
    external_job_id: Optional[int] = None  # job_id on another system
    # Remote Kaapana instance that is addressed, not external kaapana_instance_id!
    owner_kaapana_instance_name: Optional[str] = None
    service_job: Optional[bool] = False


class Job(JobBase):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    id: int
    conf_data: Optional[NestedMutableDict] = ...
    username: Optional[str] = None
    time_created: datetime.datetime
    time_updated: datetime.datetime

    @field_validator("status", mode="after")
    @classmethod
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

    @field_validator("time_created", mode="before")
    @classmethod
    def convert_time_created(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)

    @field_validator("time_updated", mode="before")
    @classmethod
    def convert_time_updated(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)


class JobCreate(JobBase):
    conf_data: dict = {}
    kaapana_instance_id: int
    username: Optional[str] = None
    automatic_execution: Optional[bool] = False


class JobUpdate(JobBase):
    # not defined in model Workflow but still needed in client.py and crud.py
    job_id: Optional[int] = None


class JobWithKaapanaInstance(Job):
    kaapana_instance: Optional[KaapanaInstance] = None


class KaapanaInstanceWithJobs(KaapanaInstance):
    jobs: List[Job] = []


class FilterKaapanaInstances(BaseModel):
    federated: bool = False
    dag_id: Optional[str] = None
    instance_names: List = []
    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None
    only_dag_names: bool = True
    kind_of_dags: Optional[str] = None


class JsonSchemaData(FilterKaapanaInstances):
    conf_data: dict = {}
    username: Optional[str] = None


class DatasetBase(BaseModel):
    name: Optional[str] = None


class DatasetCreate(DatasetBase):
    kaapana_instance_id: Optional[int] = None
    username: Optional[str] = None
    identifiers: List[str] = []


class DatasetUpdate(DatasetBase):
    action: str = ""
    identifiers: List[str] = []


class Dataset(DatasetBase):
    time_created: datetime.datetime
    time_updated: datetime.datetime
    username: Optional[str] = None
    identifiers: Optional[List[str]]

    @field_validator("time_updated", mode="before")
    @classmethod
    def convert_time_updated(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)

    model_config = ConfigDict(from_attributes=True)


class AllowedDatasetCreate(DatasetBase):
    username: Optional[str] = None
    identifiers: Optional[List[str]]
    model_config = ConfigDict(from_attributes=True)


class WorkflowBase(BaseModel):
    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None
    workflow_status: Optional[str] = None
    dag_id: Optional[str] = None
    service_workflow: Optional[bool] = False
    federated: bool = False


class Workflow(WorkflowBase):
    username: Optional[str] = None
    status: Optional[str] = None
    time_created: Optional[datetime.datetime] = None
    time_updated: Optional[datetime.datetime] = None
    automatic_execution: Optional[bool] = False
    involved_kaapana_instances: Optional[str] = None  # List = []

    @field_validator("time_created", mode="before")
    @classmethod
    def convert_time_created(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)

    @field_validator("time_updated", mode="before")
    @classmethod
    def convert_time_updated(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)

    model_config = ConfigDict(from_attributes=True)


class WorkflowCreate(WorkflowBase):
    username: Optional[str] = None
    kaapana_instance_id: int
    workflow_jobs: List = []  # List[Job] = []
    involved_kaapana_instances: list = []


class WorkflowUpdate(WorkflowBase):
    workflow_name: Optional[str] = None  # ... or workflow_name
    workflow_jobs: List = []


class WorkflowWithKaapanaInstance(Workflow):
    kaapana_instance: Optional[KaapanaInstance] = None
    # involved_kaapana_instances: list = []


class KaapanaInstanceWithWorkflows(KaapanaInstance):
    workflows: List[Workflow] = []


class JobWithWorkflow(Job):
    workflow: Optional[Workflow] = None
    # involved_kaapana_instances: Optional[list]  # idk y?


class JobWithWorkflowWithKaapanaInstance(JobWithKaapanaInstance):
    workflow: Optional[Workflow] = None


class WorkflowWithJobs(Workflow):
    jobs: List[Job] = []


class WorkflowWithKaapanaInstanceWithJobs(WorkflowWithKaapanaInstance):
    # workflow_jobs: List[Job] = []
    workflow_jobs: Optional[List]
    dataset_name: Optional[str] = None

    @model_validator(mode="after")
    def get_dataset(self) -> Self:
        # method to conclude from dataset of workflow_jobs the dataset of the workflow
        db_workflow_jobs = self.workflow_jobs
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
                self.dataset_name = dataset_name
                # after getting the dataset_name from a workflow_job, break the for loop
                break
        return self

    @model_validator(mode="after")
    def get_workflow_jobs(self) -> Self:
        # method to only list workflow_jobs' states in workflow_jobs and not whole Job object
        workflow_job_states = []
        db_workflow_jobs = self.workflow_jobs
        for db_job in db_workflow_jobs:
            if type(db_job) is not str:
                workflow_job_states.append(db_job.status)
        self.workflow_jobs = workflow_job_states
        return self
