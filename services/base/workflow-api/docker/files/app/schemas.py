from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Json
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
    metadata: Dict[str, Any] = None

class TaskBase(BaseModel):
    task_display_name: str
    type: str
    input_tasks_ids: Optional[List[str]] = None
    output_tasks_ids: Optional[List[str]] = None

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: str
    workflow_id: str

    class Config:
        from_attributes = True

class WorkflowUISchemaBase(BaseModel):
    workflow_identifier: str
    schema_definition: Dict[str, Any]

class WorkflowUISchemaCreate(WorkflowUISchemaBase):
    pass

class WorkflowUISchema(WorkflowUISchemaBase):
    workflow_version: int
    class Config:
        from_attributes = True

class TaskRunBase(BaseModel):

    is_canceled: bool = False

class TaskRunCreate(TaskRunBase):
    task_id: str
    workflow_run_id: int

class TaskRun(TaskRunBase):
    id: int
    task_id: str
    workflow_run_id: int
    lifecycle_status: LifecycleStatus

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

class WorkflowRunBase(BaseModel):
    config: Optional[dict] = {}
    is_canceled: bool = False
    labels: Dict[str, Any] = {}

class WorkflowRunCreate(WorkflowRunBase):
    pass

class WorkflowRun(WorkflowRunBase):
    id: int
    workflow_id: int    
    creation_time: datetime
    #task_runs: List[TaskRun] = []

    class Config:
        from_attributes = True