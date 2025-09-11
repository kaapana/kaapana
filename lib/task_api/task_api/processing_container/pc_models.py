from __future__ import annotations
from typing import Optional, List, Annotated
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


class EnvVarType(Enum):
    boolean = "boolean"
    string = "string"
    int = "int"


class TaskTemplateEnv(BaseModel):
    name: str
    value: str
    type: Optional[EnvVarType] = None
    choices: Optional[List[str]] = None
    adjustable: Optional[bool] = None
    description: Optional[str] = None


class Limits(BaseModel):
    cpu: Optional[str] = None
    memory: Optional[str] = None


class Requests(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    cpu: Optional[str] = None
    memory: Optional[str] = None


class Resources(BaseModel):
    limits: Optional[Limits] = None
    requests: Optional[Requests] = None


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


class IOMount(BaseModel):
    """
    Defines where an input or output channel should be mounted inside the container.
    """

    name: str
    mounted_path: str
    description: Optional[str] = None
    scale_rule: Optional[ScaleRule] = None


class TaskTemplate(BaseModel):
    """
    Blueprint for how a Docker image can be used for data processing in a predefined way.
    """

    identifier: str
    description: str
    command: List[str]
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
