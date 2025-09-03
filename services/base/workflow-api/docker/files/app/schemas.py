from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.validation.config_definition import ConfigDefinition
from enum import Enum


class LifecycleStatus(str, Enum):
    CREATED = "Created"
    PENDING = "Pending"
    SCHEDULED = "Scheduled"
    RUNNING = "Running"
    ERROR = "Error"
    COMPLETED = "Completed"
    CANCELED = "Canceled"


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
    pass


class Task(TaskBase):
    id: int
    workflow_id: int
    downstream_task_ids: List[str] = []

    model_config = ConfigDict(from_attributes=True)


#####################################
############## TASKRUN ##############
#####################################


class TaskRef(BaseModel):
    """Lightweight reference to a Task for embedding in TaskRun."""

    title: str

    model_config = ConfigDict(from_attributes=True)


class TaskRunBase(BaseModel):
    task_id: int
    workflow_run_id: int


class TaskRunCreate(TaskRunBase):
    pass


class TaskRun(TaskRunBase):
    id: int
    lifecycle_status: LifecycleStatus
    external_id: str

    model_config = ConfigDict(from_attributes=True)


class TaskRunUpdate(BaseModel):
    """Used for updating TaskRun from the workflow engine."""

    # The title of the task this run belongs to in the engine
    task_title: str
    # The unique ID of the task run in the engine (the API does not know about it when this is passed the first time, therefore we also have the task title for linking)
    external_id: str
    lifecycle_status: LifecycleStatus


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
    lifecycle_status: LifecycleStatus
    workflow: WorkflowRef
    task_runs: List[TaskRun] = Field(default_factory=list)
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunUpdate(BaseModel):
    external_id: Optional[str] = None
    lifecycle_status: Optional[LifecycleStatus]
