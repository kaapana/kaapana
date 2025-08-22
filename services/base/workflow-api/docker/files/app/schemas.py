from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Json, ConfigDict, Field
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
    creation_time: datetime

    model_config = ConfigDict(from_attributes=True)


#####################################
############## TASKS ################
#####################################


class TaskBase(BaseModel):
    display_name: Optional[str] = None
    title: str
    type: Optional[str] = None
    input_tasks_ids: Optional[List[str]] = None
    output_tasks_ids: Optional[List[str]] = None


class TaskCreate(TaskBase):
    pass


class Task(TaskBase):
    id: int
    workflow_id: int

    model_config = ConfigDict(from_attributes=True)


#####################################
############## TASKRUN ##############
#####################################


class TaskRunBase(BaseModel):
    task: Task
    workflow_run_id: int


class TaskRunCreate(TaskRunBase):
    pass


class TaskRun(TaskRunBase):
    id: int
    lifecycle_status: LifecycleStatus

    model_config = ConfigDict(from_attributes=True)


#####################################
############## WORKFLOWRUN ##########
#####################################


class WorkflowRunBase(BaseModel):
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    labels: Optional[Dict[str, Any]] = None
    workflow_version: int
    workflow_title: str


class WorkflowRunCreate(WorkflowRunBase):
    """
    Schema for the route POST /workflow-runs
    """

    pass


class WorkflowRun(WorkflowRunBase):
    id: int
    external_id: Optional[str] = None
    creation_time: datetime
    lifecycle_status: LifecycleStatus
    task_runs: List[TaskRun] = Field(default_factory=list)
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunUpdate(BaseModel):
    external_id: Optional[str]
    lifecycle_status: Optional[LifecycleStatus]
    updated_at: datetime
