from typing import List, Optional
from pydantic import BaseModel


class Policy(BaseModel):
    id: str
    name: str
    severity: str
    description: str
    categories: List[str]


class CommonEntityInfo(BaseModel):
    clusterName: str
    namespace: str
    resourceType: str


class AlertDeployment(BaseModel):
    name: str
    inactive: bool


class PolicyViolation(BaseModel):
    id: str
    lifecycleStage: str
    time: str
    policy: Policy
    state: str
    commonEntityInfo: CommonEntityInfo
    deployment: AlertDeployment
    externalUrl: str


class Image(BaseModel):
    id: str
    name: str
    registry: str
    os: Optional[str]
    cves: Optional[int]
    fixableCves: Optional[int]
    priority: str
    riskScore: int
    topCvss: Optional[int]
    externalUrl: str


class Deployment(BaseModel):
    id: str
    name: str
    namespace: str
    priority: str
    riskScore: int
    externalUrl: str


class SecretRelationship(BaseModel):
    id: str
    name: str


class Secret(BaseModel):
    id: str
    name: str
    namespace: str
    type: str
    createdAt: str
    containers: List[SecretRelationship]
    deployments: List[SecretRelationship]
    externalUrl: str
