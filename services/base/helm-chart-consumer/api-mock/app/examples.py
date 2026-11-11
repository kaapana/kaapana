"""Example data that the mock returns.

It reuses some of the applications and their deployed instances from the seed data of the UI mock in
../../docker/files/src/mock/data.ts.
"""

from datetime import UTC, datetime
from uuid import UUID

from .models import (
    Application,
    ApplicationVersion,
    BooleanParameter,
    Choice,
    ChoiceParameter,
    ConfiguredParameter,
    DryRunResult,
    HelmChartContent,
    IntegerParameter,
    ProjectPlacement,
    Release,
    ReleaseState,
    StringParameter,
    UserOrigin,
    Volume,
)


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=UTC)


JUPYTERLAB_PARAMETERS = [
    StringParameter(
        key="dataFolder",
        label="Project data folder",
        description="Folder of the project bucket that appears read-only as project-data/ in the notebook.",
        default="/",
        required=True,
        chart_value="data.projectFolder",
    ),
    ChoiceParameter(
        key="flavour",
        label="Image",
        description="Preinstalled Python packages.",
        default="scipy",
        required=True,
        choices=[
            Choice(value="minimal", label="Minimal (Python 3.12)"),
            Choice(value="scipy", label="Scientific (NumPy, SciPy, pandas)"),
            Choice(value="pytorch", label="Deep learning (PyTorch, MONAI)"),
        ],
        chart_value="image.flavour",
    ),
    BooleanParameter(
        key="gpu",
        label="Needs a GPU",
        description="Reserves one GPU while the application runs.",
        default=False,
        chart_value="resources.gpu.enabled",
    ),
    IntegerParameter(
        key="memory",
        label="Memory (GiB)",
        description="Upper memory limit of the application.",
        default=8,
        required=True,
        minimum=2,
        maximum=64,
        chart_value="resources.limits.memory",
    ),
    IntegerParameter(
        key="workspace",
        label="Workspace size (GiB)",
        description="Persistent volume for the files of the user.",
        default=10,
        required=True,
        minimum=5,
        maximum=200,
        chart_value="persistence.workspace.size",
    ),
    StringParameter(
        key="gitToken",
        label="Git access token",
        description="Lets the notebook clone private repositories.",
        default="",
        secret=True,
        chart_value="git.token",
    ),
]

IDLE_HOURS = IntegerParameter(
    key="idleHours",
    label="Stop idle kernels after (hours)",
    default=12,
    required=True,
    minimum=1,
    maximum=72,
    chart_value="jupyter.culling.idleHours",
)

JUPYTERLAB_CONTENT = HelmChartContent(
    name="jupyterlab",
    version="4.3.0",
    display_name="JupyterLab",
    description="Notebooks and a terminal for analysing the data of your project in Python.",
    multi_deployable=True,
    parameters=[*JUPYTERLAB_PARAMETERS, IDLE_HOURS],
)

JUPYTERLAB_VERSIONS = [
    ApplicationVersion(
        application_id="jupyterlab",
        version="4.3.0",
        registered_at=at(2, 9),
        content=JUPYTERLAB_CONTENT,
    ),
    ApplicationVersion(
        application_id="jupyterlab",
        version="4.2.5",
        registered_at=at(1, 9),
        content=JUPYTERLAB_CONTENT.model_copy(update={"version": "4.2.5", "parameters": JUPYTERLAB_PARAMETERS}),
    ),
]

APPLICATIONS = [
    Application(
        id="jupyterlab",
        display_name="JupyterLab",
        description=JUPYTERLAB_CONTENT.description,
        multi_deployable=True,
        latest_version="4.3.0",
        versions=["4.3.0", "4.2.5"],
        enabled_project_ids=["lung-ct", "liver-mr"],
    ),
    Application(
        id="mitk",
        display_name="MITK Workbench",
        description="MITK Workbench in the browser for viewing images and correcting segmentations.",
        multi_deployable=True,
        latest_version="2024.12.0",
        versions=["2024.12.0"],
        enabled_project_ids=["lung-ct"],
    ),
    Application(
        id="cvat",
        display_name="CVAT",
        description="Annotation tool for labelling images together with others.",
        multi_deployable=False,
        latest_version="2.11.0",
        versions=["2.11.0", "2.10.3"],
        enabled_project_ids=["lung-ct"],
    ),
    Application(
        id="collabora",
        display_name="Collabora Online",
        description="Office documents in the browser.",
        multi_deployable=False,
        latest_version="24.04.6",
        versions=["24.04.6"],
        enabled_project_ids=[],
    ),
]

ANNA_NOTEBOOK = Release(
    id=UUID("3f2a9c1e-6b4d-4e8a-9c57-1d0f8a2b7e31"),
    name="anna-notebook",
    description="Radiomics feature exploration on cohort A",
    application_id="jupyterlab",
    version="4.2.5",
    version_registered=True,
    placement=ProjectPlacement(project_id="lung-ct", deployed_for="anna"),
    state=ReleaseState.READY,
    url="/project/lung-ct/applications/anna-notebook/lab",
    parameters=[
        ConfiguredParameter(key="dataFolder", value="cohort-a", is_default=False),
        ConfiguredParameter(key="flavour", value="scipy", is_default=True),
        ConfiguredParameter(key="gpu", value=False, is_default=True),
        ConfiguredParameter(key="memory", value=8, is_default=True),
        ConfiguredParameter(key="workspace", value=10, is_default=True),
        ConfiguredParameter(key="gitToken", value=None, secret=True, is_default=False),
    ],
    volumes=[Volume(name="anna-notebook-workspace", size_gib=10)],
    origin=UserOrigin(user_id="paul"),
    deployed_at=at(6, 10),
)

SEGMENTATION_REVIEW = Release(
    id=UUID("a85e0d3c-9f17-4b62-8d4a-6c2b1e7f5093"),
    name="segmentation-review",
    description="Review and correct lung lobe segmentations before training",
    application_id="mitk",
    version="2024.06.1",
    version_registered=False,
    placement=ProjectPlacement(project_id="lung-ct"),
    state=ReleaseState.READY,
    url="/project/lung-ct/applications/segmentation-review/vnc.html",
    parameters=[
        ConfiguredParameter(key="dataFolder", value="annotations", is_default=False),
        ConfiguredParameter(key="workspace", value=5, is_default=True),
    ],
    volumes=[Volume(name="segmentation-review-workspace", size_gib=5)],
    origin=UserOrigin(user_id="paul"),
    deployed_at=at(8, 10),
)

NODULE_LABELLING = Release(
    id=UUID("e19b6f42-0a8c-4d75-b3e1-7f5a2c9d8064"),
    name="nodule-labelling",
    description="Label nodules in cohort B with the clinical team",
    application_id="cvat",
    version="2.11.0",
    version_registered=True,
    placement=ProjectPlacement(project_id="lung-ct"),
    state=ReleaseState.FAILED,
    state_reason="The container image cvat/server:2.11.0 could not be downloaded.",
    url="/project/lung-ct/applications/nodule-labelling/",
    parameters=[
        ConfiguredParameter(key="storage", value=20, is_default=True),
        ConfiguredParameter(key="adminPassword", value=None, secret=True, is_default=False),
    ],
    volumes=[Volume(name="nodule-labelling-storage", size_gib=20)],
    origin=UserOrigin(user_id="paul"),
    deployed_at=at(9, 11),
)

RELEASES = [ANNA_NOTEBOOK, SEGMENTATION_REVIEW, NODULE_LABELLING]

ANNA_NOTEBOOK_UNDEPLOYING = ANNA_NOTEBOOK.model_copy(update={"state": ReleaseState.UNDEPLOYING})

# This matches DEPLOY_REQUEST, so that the example response fits the example request.
NEW_RELEASE = ANNA_NOTEBOOK.model_copy(
    update={
        "id": UUID("7c1e4b9a-2f6d-4a83-b0c5-9e8d3f1a6b24"),
        "name": "jonas-notebook-2",
        "description": "",
        "version": "4.3.0",
        "placement": ProjectPlacement(project_id="lung-ct", deployed_for="jonas"),
        "state": ReleaseState.DEPLOYING,
        "parameters": [
            ConfiguredParameter(key="dataFolder", value="cohort-a", is_default=False),
            ConfiguredParameter(key="flavour", value="scipy", is_default=True),
            ConfiguredParameter(key="gpu", value=False, is_default=True),
            ConfiguredParameter(key="memory", value=16, is_default=False),
            ConfiguredParameter(key="workspace", value=10, is_default=True),
            ConfiguredParameter(key="gitToken", value=None, secret=True, is_default=False),
            ConfiguredParameter(key="idleHours", value=12, is_default=True),
        ],
        "url": "/project/lung-ct/applications/jonas-notebook-2/lab",
        "volumes": [Volume(name="jonas-notebook-2-workspace", size_gib=10)],
        "deployed_at": at(9, 12),
    }
)

DRY_RUN_PASSED = DryRunResult(
    problems=[],
    chart_values={
        "data": {"projectFolder": "cohort-a"},
        "image": {"flavour": "scipy"},
        "resources": {"gpu": {"enabled": False}, "limits": {"memory": 16}},
        "persistence": {"workspace": {"size": 10}},
        "git": {"token": "***"},
        "jupyter": {"culling": {"idleHours": 12}},
        "global": {
            "kaapana": {
                "application": {"id": "jupyterlab", "version": "4.3.0"},
                "project": {"id": "lung-ct"},
                "url_path": "/project/lung-ct/applications/jonas-notebook-2",
            }
        },
    },
)

DEPLOY_REQUEST = {
    "application_id": "jupyterlab",
    "version": "4.3.0",
    "name": "jonas-notebook-2",
    "placement": {"scope": "project", "project_id": "lung-ct", "deployed_for": "jonas"},
    "parameters": {"dataFolder": "cohort-a", "gpu": False, "memory": 16, "gitToken": "example-token"},
    "origin": {"type": "user"},
}

REGISTRATION_REQUEST = {
    "content": JUPYTERLAB_CONTENT.model_dump(mode="json"),
    "chart_reference": "registry.kaapana.example.org/extensions/jupyterlab-extension:4.3.0",
}
