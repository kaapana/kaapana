from enum import IntEnum
from typing import Union, List, Dict
from pydantic import BaseModel


class BaseModelExtended(BaseModel):
    """
    BaseModel that is subscriptable and supports item assignment
    """

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        return setattr(self, key, value)


class HelmInfo(BaseModelExtended):
    app_version: str
    chart: str
    name: str
    namespace: str
    revision: str  # TODO: should be int
    status: str
    updated: str  # TODO: should be date

    def __getitem__(self, item):
        return getattr(self, item)


class KubeInfo(BaseModelExtended):
    age: List[str]
    name: List[str]
    ready: List[str]
    status: List[str]
    restarts: List[str]
    annotations: Dict[str, str]  # aggreated annotations from pods and ingress objects

    def __getitem__(self, item):
        return getattr(self, item)


class KaapanaDeployment(BaseModelExtended):
    deployment_id: str
    helm_status: str
    helm_info: HelmInfo
    kube_status: Union[List[str], None, str]
    kube_info: Union[KubeInfo, None]
    links: List[str]
    ready: bool

    def __getitem__(self, item):
        return getattr(self, item)


class KaapanaAvailableVersions(BaseModelExtended):
    deployments: List[KaapanaDeployment]

    def __getitem__(self, item):
        return getattr(self, item)


class KaapanaExtension(BaseModelExtended):
    available_versions: Union[Dict[str, KaapanaAvailableVersions], None]
    chart_name: str
    description: str
    experimental: str  # TODO: make bool
    extension_params: Union[Dict, None]
    helmStatus: Union[str, None]  # TODO: name should be snake case
    installed: str  # TODO: name should be snake case
    keywords: List[str]
    kind: str
    kubeStatus: Union[str, List[str], None]  # TODO: name should be snake case
    latest_version: Union[str, None]
    multiinstallable: str  # TODO: make bool, name should be snake case
    links: Union[List[str], None]
    name: str  # TODO: same as chart_name not necessary
    releaseName: str
    resourceRequirement: str  # either cpu or gpu for now
    successful: Union[str, None]  # TODO: make bool
    version: str
    versions: List[str]
    annotations: Union[dict, None]

    # TODO: not necessary if BaseModelExtended is used
    class Config:
        allow_mutation = True

    def __getitem__(self, item):
        return getattr(self, item)


class ExtensionStateType(IntEnum):
    NOT_INSTALLED = 1
    PENDING = 2
    ERROR = 3
    INSTALLED = 4


class ExtensionStateUpdate(BaseModelExtended):
    extension_name: str
    extension_version: str
    state: ExtensionStateType
    multiinstallable: bool

    def __getitem__(self, item):
        return getattr(self, item)


class ExtensionState(BaseModelExtended):
    extension_name: str
    extension_version: str
    releaseName: str
    state: ExtensionStateType
    update_time: int
    last_read_time: int
    recently_updated: bool
    multiinstallable: bool

    def __getitem__(self, item):
        return getattr(self, item)


class ActiveApplication(BaseModelExtended):
    name: str
    namespace: str
    created_at: str
    project: str
    paths: List[str]
    annotations: Dict[str, str]
    release_name: str  # name of the deployed chart
    from_workflow_run: bool  # True if the application is triggered from a workflow run, False if it is directly installed by user
    ready: bool # Whether all pods deployed from the chart of the application are running or completed
