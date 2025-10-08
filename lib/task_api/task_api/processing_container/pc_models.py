from __future__ import annotations
from typing import Optional, List, Annotated, Dict
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


class EnvVarType(Enum):
    boolean = "boolean"
    string = "string"
    int = "int"


class BaseEnv(BaseModel):
    name: str
    value: str


class TaskTemplateEnv(BaseEnv):
    type: Optional[EnvVarType] = None
    choices: Optional[List[str]] = None
    adjustable: Optional[bool] = None
    description: Optional[str] = None


class Resources(BaseModel):
    limits: Optional[Dict] = None
    requests: Optional[Dict] = None


class ScaleRuleType(Enum):
    limit = "limit"
    request = "request"


class ScaleRuleMode(Enum):
    sum = "sum"
    max_file_size = "max_file_size"


class ScaleRule(BaseModel):
    """
    Defines how memory resources should scale based on the size of input data in an IOMount.
    """

    complexity: Annotated[str, Field(pattern="^[-+]?\\d*(\\.\\d+)?\\*?n(\\*\\*\\d+)?$")]
    type: ScaleRuleType
    mode: ScaleRuleMode
    target_dir: Optional[str] = None
    target_regex: Optional[str] = None
    target_glob: Optional[str] = None


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


class TaskTemplate(BaseModel):
    """
    Blueprint for how a Docker image can be used for data processing in a predefined way.
    """

    identifier: str
    description: str
    command: Optional[List[str]] = None
    inputs: List[IOMount]
    outputs: List[IOMount]
    env: List[TaskTemplateEnv]
    resources: Optional[Resources] = None


class ProcessingContainer(BaseModel):
    """
    Defines a processing unit that bundles multiple task templates under a single container concept.
    """

    name: str
    description: str
    templates: List[TaskTemplate]
