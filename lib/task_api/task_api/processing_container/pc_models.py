from __future__ import annotations
from typing import Optional, List, Annotated, Dict
from pydantic import BaseModel, Field
from enum import Enum


class BaseEnv(BaseModel):
    name: str
    value: str


class TaskTemplateEnv(BaseEnv):
    choices: Optional[List[str]] = None
    description: Optional[str] = None


class Resources(BaseModel):
    limits: Optional[Dict] = None
    requests: Optional[Dict] = None


class ScaleRuleType(Enum):
    limit = "limit"
    request = "request"


class ScaleRuleMode(Enum):
    sum = "sum"  ### Sum of all elements in the channel
    max_file_size = "max_file_size"  ### Maximum size of all files in all channels
    max_item_sum = "max_item_sum"  ### Maximum sum of all elements in an item subdirectory in the channel


class ScaleRule(BaseModel):
    """
    Defines how memory resources should scale based on the size of input data in an IOMount.
    """

    scale_factor: int
    type: ScaleRuleType
    mode: ScaleRuleMode
    target_dir: Optional[str] = ""
    target_regex: Optional[str] = ".*"
    target_glob: Optional[str] = "*"


class IOBase(BaseModel):
    """
    Model with common attributes for all IO related models.
    """

    name: str
    scale_rule: Optional[ScaleRule] = None


class IOMount(IOBase):
    """
    Defines where an input or output channel should be mounted inside the container.
    """

    mounted_path: str
    description: Optional[str] = None


class BaseTask(BaseModel):
    command: Optional[List[str]] = None
    resources: Optional[Resources] = None


class TaskTemplate(BaseTask):
    """
    Blueprint for how a Docker image can be used for data processing in a predefined way.
    """

    identifier: str
    description: str

    ### Common attributes for Task, TaskTemplate and TaskInstance with different types per model.
    inputs: List[IOMount]
    outputs: List[IOMount]
    env: List[TaskTemplateEnv]


class ProcessingContainer(BaseModel):
    """
    Defines a processing unit that bundles multiple task templates under a single container concept.
    """

    name: str
    description: str
    templates: List[TaskTemplate]
