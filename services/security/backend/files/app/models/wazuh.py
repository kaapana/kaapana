from typing import List, Optional
from pydantic import BaseModel


class WazuhAgent(BaseModel):
    id: str
    ip: str
    name: str
    status: str


class WazuhSCAPolicy(BaseModel):
    failed: int
    passed: int
    unapplicable: int
    name: str
    id: str


class WazuhSCAPolicyCheck(BaseModel):
    description: str
    directory: Optional[str]
    file: Optional[str]
    command: Optional[str]
    rationale: str
    references: Optional[str]
    remediation: Optional[str]
    result: str
    title: str


class WazuhAgentVulnerability(BaseModel):
    severity: str
    # updated: str;
    version: str
    type: str
    name: str
    external_references: List[str]
    condition: str
    detection_time: str
    cvss3_score: float
    cvss2_score: float
    published: str
    architecture: str
    cve: str
    status: str
    title: str


class FileIntegrityAlertRule(BaseModel):
    level: int
    description: str


class WazuhAgentFileIntegrityAlert(BaseModel):
    id: str
    path: str
    rule: FileIntegrityAlertRule
    full_log: str
