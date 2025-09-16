from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.validation.config_definition import ConfigDefinition
from enum import Enum


class WorkflowRunStatus(str, Enum):
    CREATED = "Created"
    PENDING = "Pending"
    SCHEDULED = "Scheduled"
    RUNNING = "Running"
    ERROR = "Error"
    COMPLETED = "Completed"
    CANCELED = "Canceled"


class TaskRunStatus(str, Enum):
    CREATED = "Created"
    PENDING = "Pending"
    SCHEDULED = "Scheduled"
    RUNNING = "Running"
    ERROR = "Error"
    COMPLETED = "Completed"
    SKIPPED = "Skipped"


class Label(BaseModel):
    key: str
    value: str

    model_config = ConfigDict(from_attributes=True)


#####################################
############## WORKFLOW #############
#####################################


class WorkflowBase(BaseModel):
    title: str
    definition: str
    workflow_engine: str
    config_definition: Optional[ConfigDefinition] = None
    labels: List[Label] = []


class WorkflowCreate(WorkflowBase):
    pass


class Workflow(WorkflowBase):
    id: int
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


#####################################
############## TASKS ################
#####################################


class TaskBase(BaseModel):
    display_name: Optional[str] = None
    title: str
    type: Optional[str] = None


class TaskCreate(TaskBase):
    downstream_task_titles: List[str] = []


class Task(TaskBase):
    id: int
    workflow_id: int
    downstream_task_ids: List[int] = []

    model_config = ConfigDict(from_attributes=True)


#####################################
############## TASKRUN ##############
#####################################


class TaskRunBase(BaseModel):
    task_title: str  # The title of the task this run belongs to in the engine
    lifecycle_status: TaskRunStatus
    external_id: str  # The unique ID of the task run in the engine (the API does not know about it when this is passed the first time, therefore we also have the task title for linking)


class TaskRunCreate(TaskRunBase):
    workflow_run_id: int
    task_id: int  # The title of the task this run belongs to


class TaskRun(TaskRunBase):
    id: int
    task_id: int  # The title of the task this run belongs to
    workflow_run_id: int

    model_config = ConfigDict(from_attributes=True)


class TaskRunUpdate(TaskRunBase):
    external_id: Optional[str] = None
    lifecycle_status: Optional[TaskRunStatus]


#####################################
############## WORKFLOWRUN ##########
#####################################


class WorkflowRef(BaseModel):
    """Lightweight reference to a Workflow for embedding in WorkflowRun."""

    title: str
    version: int

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunBase(BaseModel):
    workflow: WorkflowRef
    labels: List[Label] = []
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class WorkflowRunCreate(WorkflowRunBase):
    pass


class WorkflowRun(WorkflowRunBase):
    id: int
    external_id: Optional[str] = None
    created_at: datetime
    lifecycle_status: WorkflowRunStatus
    workflow: WorkflowRef
    task_runs: List[TaskRun] = Field(default_factory=list)
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunUpdate(BaseModel):
    external_id: Optional[str] = None
    lifecycle_status: Optional[WorkflowRunStatus]
