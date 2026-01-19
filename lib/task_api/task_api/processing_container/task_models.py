from __future__ import annotations
from typing import Optional, Union, List, Dict, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from task_api.processing_container import pc_models
from kubernetes import client as k8sclient


class HostPathVolume(BaseModel):
    host_path: str


class IOVolume(pc_models.IOBase):
    """
    Represents a storage location for input/output data.
    """

    volume_source: Union[k8sclient.V1Volume, HostPathVolume]
    model_config = ConfigDict(arbitrary_types_allowed=True)


class IOChannel(pc_models.IOBase):
    """
    Binds an IOMount in the container to an IOVolume in external storage.
    """

    volume_source: Union[k8sclient.V1Volume, HostPathVolume]
    model_config = ConfigDict(arbitrary_types_allowed=True)
    mounted_path: str
    description: Optional[str] = None


class BaseConfig(BaseModel):
    labels: Optional[Dict] = {}


class DockerConfig(BaseConfig):
    type: Literal["docker"] = "docker"


class K8sConfig(BaseConfig):
    type: Literal["k8s"] = "k8s"
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
    namespace: Optional[str] = None
    registryUrl: Optional[str] = None
    registryUsername: Optional[str] = None
    registryPassword: Optional[str] = None
    imagePullSecrets: Optional[List[str]] = None
    env_vars: List[k8sclient.V1EnvVar] = Field(default_factory=list)
    volumes: List[k8sclient.V1Volume] = Field(default_factory=list)
    volume_mounts: List[k8sclient.V1VolumeMount] = Field(default_factory=list)
    imagePullPolicy: Optional[str] = "Always"
    annotations: dict = {}


class Task(pc_models.BaseTask):
    """
    Concrete usage of a TaskTemplate within a workflow.
    Captures how input/output data and parameters are bound for a particular execution.
    """

    name: str
    image: str
    api_version: int = 1
    taskTemplate: Union[str, pc_models.TaskTemplate]
    config: Optional[Union[K8sConfig, DockerConfig, BaseConfig]] = BaseConfig()

    ### Common attributes for Task, TaskTemplate and TaskInstance with different types per model.
    inputs: List[IOVolume] = Field(default_factory=list)
    outputs: List[IOVolume] = Field(default_factory=list)
    env: Optional[List[pc_models.BaseEnv]] = Field(default_factory=list)

    @field_validator("api_version")
    @classmethod
    def validate_api_version(cls, v: int) -> int:
        if v != 1:
            raise ValueError("api_version must be 1")
        return v


class TaskInstance(pc_models.BaseTask):
    """
    A resolved task, created by merging the Task definition with its associated TaskTemplate.
    """

    ### Common attributes for Task, TaskTemplate and TaskInstance with different types per model.
    inputs: Optional[List[IOChannel]] = None
    outputs: Optional[List[IOChannel]] = None
    env: Optional[List[pc_models.TaskTemplateEnv]] = Field(default_factory=list)

    ### From pc_models.TaskTemplate
    identifier: str
    description: str

    ### From Task
    name: str
    image: str
    taskTemplate: Union[str, pc_models.TaskTemplate]
    config: Optional[Union[K8sConfig, DockerConfig, BaseConfig]] = BaseConfig()


class TaskRun(TaskInstance):
    """
    Execution record of a TaskInstance. Includes runtime metadata to track and identify the actual container or pod running the task.
    """

    id: str
    mode: str
