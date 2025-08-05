from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Json, ConfigDict
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
    display_name: str
    task_id: Optional[str] = None  # Optional, can be generated later
    type: str
    input_tasks_ids: Optional[List[str]] = None
    output_tasks_ids: Optional[List[str]] = None

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    workflow_id: int

    model_config = ConfigDict(from_attributes=True)

class WorkflowUISchemaBase(BaseModel):
    workflow_identifier: str
    schema_definition: Dict[str, Any]

class WorkflowUISchemaCreate(WorkflowUISchemaBase):
    pass

class WorkflowUISchema(WorkflowUISchemaBase):
    workflow_version: int

    model_config = ConfigDict(from_attributes=True)
class TaskRunBase(BaseModel):
    pass

class TaskRunCreate(TaskRunBase):
    task_id: str
    workflow_run_id: int

class TaskRun(TaskRunBase):
    id: int
    workflow_run_id: int
    lifecycle_status: LifecycleStatus
    task: Task

    model_config = ConfigDict(from_attributes=True)

class WorkflowBase(BaseModel):
    definition: str
    config_definition: Optional[dict] = {}

class WorkflowCreate(WorkflowBase):
    identifier: str

class Workflow(WorkflowBase):
    id: int
    identifier: str
    version: Optional[int] = None  # Make version optional and default to None
    creation_time: datetime
    tasks: List[Task] = []

    model_config = ConfigDict(from_attributes=True)

class WorkflowRunBase(BaseModel):
    config: Optional[dict] = {}
    labels: Dict[str, Any] = {}

class WorkflowRunCreate(WorkflowRunBase):
    pass

class WorkflowRun(WorkflowRunBase):
    id: int
    workflow_id: int    
    external_id_: Optional[str] = None
    creation_time: datetime
    lifecycle_status: LifecycleStatus
    task_runs: List[TaskRun] = []
    model_config = ConfigDict(from_attributes=True)