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
        description="A secret value is set as a chart value like every other parameter. The Helm Chart Consumer "
        "never returns it.",
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
    multi_deployable: bool = Field(
        False,
        description="If true, the application can have several releases in the same project.",
    )
    parameters: list[ParameterDeclaration] = []


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
    multi_deployable: bool
    latest_version: str
    versions: list[str] = Field(description="Registered versions, newest first by semantic version.")
    enabled_project_ids: list[str] = Field(
        description="These are the projects in which the application is enabled. A kaapana-system-admin gets all of "
        "them. Every other user gets only the projects in which they may deploy."
    )


class ProjectPlacement(Strict):
    scope: Literal["project"] = "project"
    project_id: str
    deployed_for: str | None = Field(
        None,
        description="User the release is meant for, or null for the whole project. "
        "Every member of the project can open it either way.",
    )


class UserOrigin(Strict):
    """A user deployed the release through the gateway."""

    type: Literal["user"] = "user"
    user_id: str | None = Field(
        None,
        description="This is the user who deploys. A request can leave it out, and the Helm Chart Consumer then sets "
        "it to the calling user. A response always contains it.",
    )


class ReleaseCreate(Strict):
    application_id: str
    version: str | None = Field(None, description="A registered version. The newest one if omitted.")
    name: str = Field(min_length=3, max_length=30, pattern=r"^[a-z]([a-z0-9-]*[a-z0-9])?$")
    description: str = Field("", max_length=200)
    placement: ProjectPlacement
    parameters: dict[str, ParameterValue] = Field(
        {}, description="Values for declared parameters. Others get their default."
    )
    origin: UserOrigin = Field(
        UserOrigin(),
        description="The origin says who deploys the application. A user origin must name the calling user or "
        "leave `user_id` out.",
    )


class DryRunResult(BaseModel):
    problems: list[str] = Field(description="Why the request would fail. Empty if it would succeed.")
    chart_values: dict[str, Any] = Field(
        description="The chart values that the deploy would set. A secret parameter shows a placeholder. The values "
        "that the Helm Chart Consumer copies from the platform into `global` are left out, because some of them are "
        "passwords of the platform. The values under `global.kaapana` are shown."
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
    placement: ProjectPlacement
    state: ReleaseState
    state_reason: str | None = None
    url: str | None = Field(
        description="This is the path of the web interface on the Kaapana host. The Helm Chart Consumer reads it "
        "from the `Ingress` that the chart marks as its web interface. It is null if the chart has none."
    )
    parameters: list[ConfiguredParameter]
    volumes: list[Volume] = Field(description="Persistent volumes. Undeploying deletes them with their data.")
    origin: UserOrigin = Field(description="The origin says who deployed the release. It never changes.")
    deployed_at: datetime
