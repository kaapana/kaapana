from typing import Union, List, Dict
from pydantic import BaseModel


class HelmInfo(BaseModel):
    app_version: str
    chart: str
    name: str
    namespace: str
    revision: str  # TODO: should be int
    status: str
    updated: str  # TODO: should be date

    def __getitem__(self, item):
        return getattr(self, item)


class KubeInfo(BaseModel):
    age: List[str]
    name: List[str]
    ready: List[str]
    status: List[str]
    restarts: List[str]

    def __getitem__(self, item):
        return getattr(self, item)


class KaapanaDeployment(BaseModel):
    deployment_id: str
    helm_status: str
    helm_info: HelmInfo
    kube_status: List[str]
    kube_info: Union[KubeInfo, None]
    links: List[str]
    ready: bool

    def __getitem__(self, item):
        return getattr(self, item)


class KaapanaAvailableVersions(BaseModel):
    deployments: List[KaapanaDeployment]

    def __getitem__(self, item):
        return getattr(self, item)


class KaapanaExtension(BaseModel):
    available_versions: Union[Dict[str, KaapanaAvailableVersions], None]
    chart_name: str
    description: str
    experimental: str  # TODO: make bool
    helmStatus: str  # TODO: name should be snake case
    installed: str  # TODO: name should be snake case
    keywords: List[str]
    kind: str
    kubeStatus: Union[str, List[str]]  # TODO: name should be snake case
    latest_version: Union[str, None]
    multiinstallable: str  # TODO: make bool, name should be snake case
    links: Union[List[int], None]
    name: str  # TODO: same as chart_name not necessary
    releaseName: str
    successful: str  # TODO: make bool
    version: str
    versions: List[str]

    def __getitem__(self, item):
        return getattr(self, item)
