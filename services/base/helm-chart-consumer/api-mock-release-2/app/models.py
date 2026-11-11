"""Request and response models of the Helm Chart Consumer API."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ParameterValue = str | int | bool


class Strict(BaseModel):
    """Rejects unknown fields, so that a typo in a request fails instead of being ignored."""

    model_config = ConfigDict(extra="forbid")


class Scope(StrEnum):
    PROJECT = "project"
    PLATFORM = "platform"


class ReleaseState(StrEnum):
    """The state of a release.

    Helm reports a helm release as `deployed` as soon as it has applied the manifests. This state
    also says whether the application is ready to use. A release is `ready` when every object of
    its helm release is ready. It is `failed` when a helm command or an object failed. It is also
    `failed` when it is not ready after a deadline, because an object whose pods crash-loop can
    stay in progress forever.
    """

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


class PatchTarget(Strict):
    """This names one object of the rendered chart by its kind and its name."""

    kind: str
    name: str


class PatchOperation(Strict):
    op: Literal["add", "replace"] = Field(
        description="`add` writes a field, and creates it if the object does not have it. `replace` overwrites a "
        "field that the object already has, and fails if the field is missing."
    )
    path: str = Field(description="This is the path to a field of the object, written as in JSON Patch.")
    value: Any


class Patch(Strict):
    """A patch changes one object of the rendered chart."""

    target: PatchTarget
    operations: list[PatchOperation]


class HelmChartContent(Strict):
    """The part of a helm-chart content that Kaapana reads.

    Extension developers write it as `helm-chart-content.json`.
    """

    name: str
    version: str = Field(
        description="This is the version of the content. It must be a semantic version. The Helm Chart Consumer "
        "does not look at the version of the extension."
    )
    display_name: str
    description: str
    scopes: list[Scope] = Field([Scope.PROJECT], min_length=1)
    multi_deployable: bool = Field(
        False,
        description="If true, the application can be deployed several times in the same scope. A scope is one "
        "project or the whole platform.",
    )
    parameters: list[ParameterDeclaration] = []
    platform_secrets: list[str] = Field(
        [],
        description="These are the names of the privileged values that a platform content needs. The Helm Chart "
        "Consumer passes them under `global.kaapana.secrets`. A registration by the Extension Manager that declares "
        "them is rejected.",
    )
    platform_value_mapping: dict[str, str] = Field(
        {},
        description="Each entry maps the name of a platform value to the dotted path of the chart value that receives "
        "it. The path must exist in `values.yaml`, and no parameter may name it as its `chart_value`.",
    )
    patches: list[Patch] = Field(
        [],
        description="The Helm Chart Consumer applies these patches to the rendered chart. A patch that matches no "
        "object is rejected at registration.",
    )


class VersionRegistration(Strict):
    content: HelmChartContent
    chart_reference: str = Field(description="Where the Helm Chart Consumer fetches the packaged chart from.")


class ApplicationVersion(BaseModel):
    application_id: str
    version: str
    registered_at: datetime
    deregistered_at: datetime | None = Field(
        None, description="Null while the version is registered. Set when the version is deregistered."
    )
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
    enabled_project_ids: list[str] = Field(
        description="These are the projects in which the application is enabled. A kaapana-system-admin gets all of "
        "them. Every other user gets only the projects in which they may deploy."
    )


class ProjectPlacement(Strict):
    scope: Literal[Scope.PROJECT] = Scope.PROJECT
    project_id: str
    deployed_for: str | None = Field(
        None,
        description="User the release is meant for, or null for the whole project. "
        "Every member of the project can open it either way.",
    )


class PlatformPlacement(Strict):
    scope: Literal[Scope.PLATFORM] = Scope.PLATFORM


Placement = Annotated[ProjectPlacement | PlatformPlacement, Field(discriminator="scope")]


class UserOrigin(Strict):
    """A user deployed the release through the gateway."""

    type: Literal["user"] = "user"
    user_id: str | None = Field(
        None,
        description="This is the user who deploys. A request can leave it out, and the Helm Chart Consumer then sets "
        "it to the calling user. A response always contains it.",
    )


class WorkflowOrigin(Strict):
    """A workflow task deployed the release."""

    type: Literal["workflow"] = "workflow"
    workflow_run_id: str
    task_id: str
    started_by: str | None = Field(
        None, description="This is the user who started the workflow run. It is missing when no user started the run."
    )


class ServiceOrigin(Strict):
    """A platform service deployed the release."""

    type: Literal["service"] = "service"
    service: str = Field(
        description="This is the name of the platform service that deployed the release, for example "
        "`access-information-interface`."
    )


Origin = Annotated[UserOrigin | WorkflowOrigin | ServiceOrigin, Field(discriminator="type")]


class ReleaseCreate(Strict):
    application_id: str
    version: str | None = Field(None, description="A registered version. The newest one if omitted.")
    name: str = Field(min_length=3, max_length=30, pattern=r"^[a-z]([a-z0-9-]*[a-z0-9])?$")
    description: str = Field("", max_length=200)
    placement: Placement
    parameters: dict[str, ParameterValue] = Field(
        {}, description="Values for declared parameters. Others get their default."
    )
    origin: Origin = Field(
        UserOrigin(),
        description="The origin says who or what deploys the application. A user origin must name the calling user or "
        "leave `user_id` out. Only workflow-api may send a workflow origin. Only a platform service may send a "
        "service origin.",
    )


class ReleaseUpdate(Strict):
    version: str | None = Field(None, description="Another registered version. The current one if omitted.")
    parameters: dict[str, ParameterValue | None] = Field(
        {},
        description="Changed values. Null resets a parameter to its default. "
        "Parameters that are left out keep their value.",
    )


class DryRunResult(BaseModel):
    problems: list[str] = Field(description="Why the request would fail. Empty if it would succeed.")
    chart_values: dict[str, Any] = Field(
        description="The values helm would receive. A secret parameter appears as the name of its Kubernetes secret. "
        "A privileged value of a platform content is never returned. The result only shows that it is set."
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


class Release(BaseModel):
    """The Helm Chart Consumer's record of the helm release it creates from a version of an application.

    The record also holds what helm does not know, such as the placement and who deployed it. It
    exists as soon as a deploy passes its checks, before helm has installed anything.
    """

    id: UUID = Field(
        description="The Helm Chart Consumer generates this id when it creates the release. The id never changes. "
        "The routes of a single release take it in the path."
    )
    name: str = Field(description="Human-readable name. Part of the path of the web interface.")
    description: str
    application_id: str
    version: str
    version_registered: bool = Field(description="False if the version was deregistered after the deploy.")
    newer_version: str | None = Field(description="The newest registered version, if it is newer than `version`.")
    placement: Placement
    state: ReleaseState
    state_reason: str | None = None
    url: str | None = Field(
        description="This is the path of the web interface on the Kaapana host. The Helm Chart Consumer reads it "
        "from the `Ingress` that the chart marks as its web interface. It is null if the chart has none."
    )
    parameters: list[ConfiguredParameter]
    volumes: list[Volume] = Field(description="Persistent volumes. Undeploying deletes them with their data.")
    origin: Origin = Field(description="The origin says who or what deployed the release. It never changes.")
    deployed_at: datetime
    updated_at: datetime


class Resource(BaseModel):
    """A Kubernetes object in the manifest of the helm release."""

    kind: str
    name: str
    state: Literal["ready", "in_progress", "failed", "missing"] = Field(
        description="`missing` means that the object is in the manifest but not in the cluster."
    )
    message: str | None = Field(None, description="What the object reports, e.g. 1 of 2 replicas available.")


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


class ReleaseStatus(BaseModel):
    """What the cluster reports about a release. The state and its reason are fields of the release."""

    helm_error: str | None = Field(None, description="Output of the last failed helm command.")
    resources: list[Resource]
    pods: list[Pod] = Field(description="Pods are not in the manifest, because controllers create them.")
    events: list[Event]
    checked_at: datetime
