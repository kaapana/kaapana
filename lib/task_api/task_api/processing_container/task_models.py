from __future__ import annotations
from typing import Optional, Union, List, Dict, Literal
from pydantic import BaseModel, ConfigDict
from task_api.processing_container import pc_models
from kubernetes import client as k8sclient


class HostPathVolume(BaseModel):
    host_path: str


class IOVolume(BaseModel):
    """
    Represents a storage location for input/output data.
    """

    name: str
    scale_rule: Optional[pc_models.ScaleRule] = None
    input: Union[k8sclient.V1Volume, HostPathVolume]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class IOChannel(pc_models.IOMount, IOVolume):
    """
    Binds an IOMount in the container to an IOVolume in external storage.
    """


class TaskEnvVar(BaseModel):
    """ """

    name: str
    value: str


class BaseConfig(BaseModel):
    labels: Optional[Dict] = {}


class DockerConfig(BaseConfig):
    type: Literal["docker"] = "docker"


class K8sConfig(BaseConfig):
    type: Literal["k8s"] = "k8s"
    model_config = ConfigDict(arbitrary_types_allowed=True)
    namespace: Optional[str] = None
    registryUrl: Optional[str] = None
    registryUsername: Optional[str] = None
    registryPassword: Optional[str] = None
    imagePullSecrets: Optional[List[str]] = None
    env_vars: List[k8sclient.V1EnvVar] = []
    volumes: List[k8sclient.V1Volume] = []
    volume_mounts: List[k8sclient.V1VolumeMount] = []
    annotations: dict = {}


class Task(BaseModel):
    """
    Concrete usage of a TaskTemplate within a workflow.
    Captures how input/output data and parameters are bound for a particular execution.
    """

    name: str
    image: str
    taskTemplate: Union[str, pc_models.TaskTemplate]
    command: Optional[List[str]] = None
    inputs: List[IOVolume] = []
    outputs: List[IOVolume] = []
    env: Optional[List[TaskEnvVar]] = []
    resources: Optional[pc_models.Resources] = None

    config: Optional[Union[DockerConfig, K8sConfig]] = None


class TaskInstanceEnv(pc_models.TaskTemplateEnv, TaskEnvVar):
    pass


class TaskInstance(Task, pc_models.TaskTemplate):
    """
    A resolved task, created by merging the Task definition with its associated TaskTemplate.
    """

    inputs: Optional[List[IOChannel]] = None
    outputs: Optional[List[IOChannel]] = None
    env: Optional[List[TaskInstanceEnv]] = []


class TaskRun(TaskInstance):
    """
    Execution record of a TaskInstance. Includes runtime metadata to track and identify the actual container or pod running the task.
    """

    id: str
    mode: str
