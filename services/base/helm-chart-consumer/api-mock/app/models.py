"""Request and response models of the Helm Chart Consumer API."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ParameterValue = str | int | bool


class Strict(BaseModel):
    """Rejects unknown fields, so that a typo in a request fails instead of being ignored."""

    model_config = ConfigDict(extra="forbid")


class Scope(StrEnum):
    PROJECT = "project"
    PLATFORM = "platform"


class DeploymentState(StrEnum):
    DEPLOYING = "deploying"
    READY = "ready"
    FAILED = "failed"
    UPDATING = "updating"
    UNDEPLOYING = "undeploying"


class Error(BaseModel):
    detail: str


class ParameterBase(Strict):
    key: str
    label: str
    description: str = ""
    required: bool = Field(False, description="A required parameter cannot be left empty.")
    chart_value: str = Field(description="Dotted path of the chart value that receives the parameter.")


class StringParameter(ParameterBase):
    type: Literal["string"] = "string"
    default: str | None = None
    pattern: str | None = Field(None, description="Regular expression that the value must match.")
    secret: bool = Field(
        False,
        description="A secret value is stored in a Kubernetes secret and never returned. The chart value receives "
        "the name of that secret, so that the value stays out of the helm release.",
    )


class IntegerParameter(ParameterBase):
    type: Literal["integer"] = "integer"
    default: int | None = None
    minimum: int | None = None
    maximum: int | None = None


class BooleanParameter(ParameterBase):
    type: Literal["boolean"] = "boolean"
    default: bool = False


class Choice(Strict):
    value: str
    label: str


class ChoiceParameter(ParameterBase):
    type: Literal["choice"] = "choice"
    default: str | None = None
    choices: list[Choice] = Field(min_length=1)


ParameterDeclaration = Annotated[
    StringParameter | IntegerParameter | BooleanParameter | ChoiceParameter, Field(discriminator="type")
]


class WebInterface(Strict):
    service: str
    port: int
    path: str = "/"


class HelmChartContent(Strict):
    """The part of a helm-chart content that Kaapana reads.

    Extension developers write it as `helm-chart-content.json`.
    """

    name: str
    display_name: str
    description: str
    scopes: list[Scope] = Field([Scope.PROJECT], min_length=1)
    multi_deployable: bool = Field(
        False, description="Whether the application can be deployed several times in one project."
    )
    web_interface: WebInterface | None = None
    parameters: list[ParameterDeclaration] = []


class ExtensionReference(Strict):
    id: str
    name: str
    version: str


class VersionRegistration(Strict):
    extension: ExtensionReference
    content: HelmChartContent
    chart_reference: str = Field(description="Where the Helm Chart Consumer fetches the packaged chart from.")


class ApplicationVersion(BaseModel):
    application_id: str
    version: str
    registered_at: datetime
    deregistered_at: datetime | None = Field(
        None, description="Null while the version is registered. Set when its extension is uninstalled."
    )
    extension: ExtensionReference
    content: HelmChartContent


class Application(BaseModel):
    """A helm-chart content with all its registered versions."""

    id: str
    display_name: str
    description: str
    scopes: list[Scope]
    multi_deployable: bool
    latest_version: str
    versions: list[str] = Field(description="Registered versions, newest first by semantic version.")


class ProjectPlacement(Strict):
    scope: Literal[Scope.PROJECT] = Scope.PROJECT
    project_id: str
    deployed_for: str | None = Field(
        None,
        description="User the deployment is meant for, or null for the whole project. "
        "Every member of the project can open it either way.",
    )


class PlatformPlacement(Strict):
    scope: Literal[Scope.PLATFORM] = Scope.PLATFORM


Placement = Annotated[ProjectPlacement | PlatformPlacement, Field(discriminator="scope")]


class WorkflowOrigin(Strict):
    workflow_run_id: str
    task_id: str


class DeploymentCreate(Strict):
    application_id: str
    version: str | None = Field(None, description="A registered version. The newest one if omitted.")
    name: str = Field(min_length=3, max_length=30, pattern=r"^[a-z]([a-z0-9-]*[a-z0-9])?$")
    description: str = Field("", max_length=200)
    placement: Placement
    parameters: dict[str, ParameterValue] = Field(
        {}, description="Values for declared parameters. Others get their default."
    )
    workflow: WorkflowOrigin | None = Field(None, description="Set when a workflow task deploys the application.")


class DeploymentUpdate(Strict):
    version: str | None = Field(None, description="Another registered version. The current one if omitted.")
    parameters: dict[str, ParameterValue | None] = Field(
        {},
        description="Changed values. Null resets a parameter to its default. "
        "Parameters that are left out keep their value.",
    )


class DryRunResult(BaseModel):
    problems: list[str] = Field(description="Why the request would fail. Empty if it would succeed.")
    chart_values: dict[str, Any] = Field(
        description="The values helm would receive. A secret parameter appears as the name of its Kubernetes secret."
    )


class ConfiguredParameter(BaseModel):
    key: str
    value: ParameterValue | None = Field(description="Null for secret parameters.")
    secret: bool = False
    is_set: bool = Field(True, description="False if the parameter is empty. A secret shows this instead of its value.")
    is_default: bool


class Volume(BaseModel):
    name: str
    size_gib: int


class Drift(BaseModel):
    kind: Literal["changed", "removed"] = Field(
        description="What happened to the helm release outside the Helm Chart Consumer."
    )
    detected_at: datetime


class Deployment(BaseModel):
    """An instance of an application, i.e. a helm release created by the Helm Chart Consumer."""

    id: str
    name: str = Field(description="Human-readable name. Part of the path of the web interface.")
    description: str
    application_id: str
    version: str
    version_registered: bool = Field(description="False if the version was deregistered after the deploy.")
    newer_version: str | None = Field(description="The newest registered version, if it is newer than `version`.")
    placement: Placement
    state: DeploymentState
    state_reason: str | None = None
    drift: Drift | None = Field(
        None, description="Set when the helm release was changed or removed outside the Helm Chart Consumer."
    )
    url: str | None = Field(description="Path of the web interface on the Kaapana host, if the application has one.")
    parameters: list[ConfiguredParameter]
    volumes: list[Volume] = Field(description="Persistent volumes. Undeploying deletes them with their data.")
    workflow: WorkflowOrigin | None = None
    deployed_by: str
    deployed_at: datetime
    updated_at: datetime


class Pod(BaseModel):
    name: str
    phase: Literal["Pending", "Running", "Succeeded", "Failed", "Unknown"]
    reason: str | None = Field(None, description="Why a container is waiting or was stopped, e.g. ImagePullBackOff.")
    ready: str = Field(description="Ready containers out of all containers, e.g. 1/1.")
    restarts: int
    started_at: datetime | None = Field(description="Null until a node has accepted the pod.")
    containers: list[str]


class Event(BaseModel):
    type: Literal["Normal", "Warning"]
    reason: str
    object: str
    message: str
    timestamp: datetime


class DeploymentStatus(BaseModel):
    """What the cluster reports about a deployment. The state and its reason are fields of the deployment."""

    helm_error: str | None = Field(None, description="Output of the last failed helm command.")
    pods: list[Pod]
    events: list[Event]
    checked_at: datetime


class Enablement(BaseModel):
    project_id: str
    application_id: str
    enabled_by: str
    enabled_at: datetime
