from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Json, ConfigDict, Field
from app.validation.config_definition import ConfigDefinition
from enum import Enum


class LifecycleStatus(str, Enum):
    PENDING = "Pending"
    SCHEDULED = "Scheduled"
    RUNNING = "Running"
    ERROR = "Error"
    COMPLETED = "Completed"
    CANCELED = "Canceled"


@dataclass
class WorkflowRunResult:
    """Result of a workflow run operation"""

    workflow_run_id: int
    external_id: Optional[str] = None
    status: LifecycleStatus = LifecycleStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskBase(BaseModel):
    display_name: Optional[str] = None
    task_identifier: str
    type: Optional[str] = None
    input_tasks_ids: Optional[List[str]] = None
    output_tasks_ids: Optional[List[str]] = None


class TaskCreate(TaskBase):
    pass


class Task(TaskBase):
    id: int
    workflow_id: int

    model_config = ConfigDict(from_attributes=True)


class WorkflowUISchemaBase(BaseModel):
    schema_definition: Optional[dict] = Field(default_factory=dict)


class WorkflowUISchemaCreate(WorkflowUISchemaBase):
    pass


class WorkflowUISchema(WorkflowUISchemaBase):
    workflow_id: int

    model_config = ConfigDict(from_attributes=True)


class TaskRunBase(BaseModel):
    task_id: int
    workflow_run_id: int


class TaskRunCreate(TaskRunBase):
    pass


class TaskRun(TaskRunBase):
    id: int
    lifecycle_status: LifecycleStatus
    task: Task

    model_config = ConfigDict(from_attributes=True)


class WorkflowBase(BaseModel):
    definition: str
    config_definition: Optional[ConfigDefinition] = None 

class WorkflowCreate(WorkflowBase):
    identifier: str


class Workflow(WorkflowBase):
    id: int
    identifier: str
    version: int
    creation_time: datetime
    tasks: List[Task] = Field(default_factory=list)
    # ui_schema_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunBase(BaseModel):
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    labels: Optional[Dict[str, Any]] = None


class WorkflowRunCreate(WorkflowRunBase):
    pass


class WorkflowRun(WorkflowRunBase):
    id: int
    workflow_id: int
    external_id: Optional[str] = None
    creation_time: datetime
    lifecycle_status: LifecycleStatus
    task_runs: List[TaskRun] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
