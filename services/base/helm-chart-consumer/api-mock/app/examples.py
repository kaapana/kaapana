"""Example data that the mock returns.

It reuses some of the applications and their deployed instances from the seed data of the UI mock in
../../docker/files/src/mock/data.ts.
"""

from datetime import UTC, datetime

from .models import (
    Application,
    ApplicationVersion,
    BooleanParameter,
    Choice,
    ChoiceParameter,
    ConfiguredParameter,
    DryRunResult,
    Enablement,
    Event,
    ExtensionReference,
    HelmChartContent,
    IntegerParameter,
    PlatformPlacement,
    Pod,
    ProjectPlacement,
    Release,
    ReleaseState,
    ReleaseStatus,
    Scope,
    StringParameter,
    Volume,
    WebInterface,
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
        chart_value="git.tokenSecret",
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
    display_name="JupyterLab",
    description="Notebooks and a terminal for analysing the data of your project in Python.",
    scopes=[Scope.PROJECT],
    multi_deployable=True,
    web_interface=WebInterface(service="jupyterlab", port=8888, path="/lab"),
    parameters=[*JUPYTERLAB_PARAMETERS, IDLE_HOURS],
)

JUPYTERLAB_EXTENSION = ExtensionReference(id="jupyterlab-extension", name="jupyterlab-extension", version="4.3.0")

JUPYTERLAB_VERSIONS = [
    ApplicationVersion(
        application_id="jupyterlab",
        version="4.3.0",
        registered_at=at(2, 9),
        extension=JUPYTERLAB_EXTENSION,
        content=JUPYTERLAB_CONTENT,
    ),
    ApplicationVersion(
        application_id="jupyterlab",
        version="4.2.5",
        registered_at=at(1, 9),
        extension=JUPYTERLAB_EXTENSION.model_copy(update={"version": "4.2.5"}),
        content=JUPYTERLAB_CONTENT.model_copy(update={"parameters": JUPYTERLAB_PARAMETERS}),
    ),
]

APPLICATIONS = [
    Application(
        id="jupyterlab",
        display_name="JupyterLab",
        description=JUPYTERLAB_CONTENT.description,
        scopes=[Scope.PROJECT],
        multi_deployable=True,
        latest_version="4.3.0",
        versions=["4.3.0", "4.2.5"],
    ),
    Application(
        id="mitk",
        display_name="MITK Workbench",
        description="MITK Workbench in the browser for viewing images and correcting segmentations.",
        scopes=[Scope.PROJECT],
        multi_deployable=True,
        latest_version="2024.12.0",
        versions=["2024.12.0"],
    ),
    Application(
        id="cvat",
        display_name="CVAT",
        description="Annotation tool for labelling images together with others.",
        scopes=[Scope.PROJECT],
        multi_deployable=False,
        latest_version="2.11.0",
        versions=["2.11.0", "2.10.3"],
    ),
    Application(
        id="collabora",
        display_name="Collabora Online",
        description="Office documents in the browser.",
        scopes=[Scope.PROJECT, Scope.PLATFORM],
        multi_deployable=False,
        latest_version="24.04.6",
        versions=["24.04.6"],
    ),
    Application(
        id="ohif",
        display_name="OHIF Viewer",
        description="DICOM viewer for the images of a project.",
        scopes=[Scope.PLATFORM],
        multi_deployable=False,
        latest_version="3.8.2",
        versions=["3.8.2"],
    ),
]

ANNA_NOTEBOOK = Release(
    id="d1",
    name="anna-notebook",
    description="Radiomics feature exploration on cohort A",
    application_id="jupyterlab",
    version="4.2.5",
    version_registered=True,
    newer_version="4.3.0",
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
    deployed_by="paul",
    deployed_at=at(6, 10),
    updated_at=at(6, 10),
)

SEGMENTATION_REVIEW = Release(
    id="d3",
    name="segmentation-review",
    description="Review and correct lung lobe segmentations before training",
    application_id="mitk",
    version="2024.06.1",
    version_registered=False,
    newer_version="2024.12.0",
    placement=ProjectPlacement(project_id="lung-ct"),
    state=ReleaseState.READY,
    url="/project/lung-ct/applications/segmentation-review/vnc.html",
    parameters=[
        ConfiguredParameter(key="dataFolder", value="annotations", is_default=False),
        ConfiguredParameter(key="workspace", value=5, is_default=True),
    ],
    volumes=[Volume(name="segmentation-review-workspace", size_gib=5)],
    deployed_by="paul",
    deployed_at=at(8, 10),
    updated_at=at(8, 10),
)

NODULE_LABELLING = Release(
    id="d4",
    name="nodule-labelling",
    description="Label nodules in cohort B with the clinical team",
    application_id="cvat",
    version="2.11.0",
    version_registered=True,
    newer_version=None,
    placement=ProjectPlacement(project_id="lung-ct"),
    state=ReleaseState.FAILED,
    state_reason="The container image cvat/server:2.11.0 could not be downloaded.",
    url="/project/lung-ct/applications/nodule-labelling/",
    parameters=[
        ConfiguredParameter(key="storage", value=20, is_default=True),
        ConfiguredParameter(key="adminPassword", value=None, secret=True, is_default=False),
    ],
    volumes=[Volume(name="nodule-labelling-storage", size_gib=20)],
    deployed_by="paul",
    deployed_at=at(9, 11),
    updated_at=at(9, 11),
)

OHIF = Release(
    id="d10",
    name="ohif",
    description="DICOM viewer for all projects",
    application_id="ohif",
    version="3.8.2",
    version_registered=True,
    newer_version=None,
    placement=PlatformPlacement(),
    state=ReleaseState.READY,
    url="/applications/ohif/viewer",
    parameters=[ConfiguredParameter(key="layout", value="1x1", is_default=True)],
    volumes=[],
    deployed_by="kim",
    deployed_at=at(19, 9),
    updated_at=at(19, 9),
)

RELEASES = [ANNA_NOTEBOOK, SEGMENTATION_REVIEW, NODULE_LABELLING, OHIF]

ANNA_NOTEBOOK_UNDEPLOYING = ANNA_NOTEBOOK.model_copy(update={"state": ReleaseState.UNDEPLOYING})

# This matches UPDATE_REQUEST, so that the example response fits the example request.
ANNA_NOTEBOOK_UPDATING = ANNA_NOTEBOOK.model_copy(
    update={
        "version": "4.3.0",
        "newer_version": None,
        "state": ReleaseState.UPDATING,
        "parameters": [
            ConfiguredParameter(key="dataFolder", value="cohort-a", is_default=False),
            ConfiguredParameter(key="flavour", value="scipy", is_default=True),
            ConfiguredParameter(key="gpu", value=False, is_default=True),
            ConfiguredParameter(key="memory", value=16, is_default=False),
            ConfiguredParameter(key="workspace", value=10, is_default=True),
            ConfiguredParameter(key="gitToken", value=None, secret=True, is_default=False),
            ConfiguredParameter(key="idleHours", value=12, is_default=True),
        ],
        "updated_at": at(9, 12),
    }
)

# This matches DEPLOY_REQUEST, so that the example response fits the example request.
NEW_RELEASE = ANNA_NOTEBOOK.model_copy(
    update={
        "id": "d11",
        "name": "jonas-notebook-2",
        "description": "",
        "version": "4.3.0",
        "newer_version": None,
        "placement": ProjectPlacement(project_id="lung-ct", deployed_for="jonas"),
        "state": ReleaseState.DEPLOYING,
        "parameters": [
            ConfiguredParameter(key="dataFolder", value="cohort-a", is_default=False),
            ConfiguredParameter(key="flavour", value="scipy", is_default=True),
            ConfiguredParameter(key="gpu", value=False, is_default=True),
            ConfiguredParameter(key="memory", value=16, is_default=False),
            ConfiguredParameter(key="workspace", value=10, is_default=True),
            ConfiguredParameter(key="gitToken", value=None, secret=True, is_set=False, is_default=True),
            ConfiguredParameter(key="idleHours", value=12, is_default=True),
        ],
        "url": "/project/lung-ct/applications/jonas-notebook-2/lab",
        "volumes": [Volume(name="jonas-notebook-2-workspace", size_gib=10)],
        "deployed_at": at(9, 12),
        "updated_at": at(9, 12),
    }
)

ANNA_NOTEBOOK_STATUS = ReleaseStatus(
    pods=[
        Pod(
            name="anna-notebook-jupyterlab-6c9f7d8b5-x2k4q",
            phase="Running",
            ready="1/1",
            restarts=0,
            started_at=at(6, 10, 1),
            containers=["jupyterlab"],
        )
    ],
    events=[
        Event(
            type="Normal",
            reason="Started",
            object="pod/anna-notebook-jupyterlab-6c9f7d8b5-x2k4q",
            message="Started container jupyterlab",
            timestamp=at(6, 10, 1),
        )
    ],
    checked_at=at(9, 12),
)

DRY_RUN_PASSED = DryRunResult(
    problems=[],
    chart_values={
        "data": {"projectFolder": "cohort-a"},
        "image": {"flavour": "scipy"},
        "resources": {"gpu": {"enabled": False}, "limits": {"memory": 16}},
        "persistence": {"workspace": {"size": 10}},
        "jupyter": {"culling": {"idleHours": 12}},
    },
)

UPDATE_DRY_RUN_PASSED = DryRunResult(
    problems=[],
    chart_values={**DRY_RUN_PASSED.chart_values, "git": {"tokenSecret": "anna-notebook-git-token"}},
)

ANNA_NOTEBOOK_LOGS = """\
[I 2026-11-06 10:01:12.204 ServerApp] jupyterlab | extension was successfully loaded.
[I 2026-11-06 10:01:12.391 ServerApp] Serving notebooks from local directory: /home/jovyan/work
[I 2026-11-06 10:01:12.392 ServerApp] Jupyter Server is running at /project/lung-ct/applications/anna-notebook/lab
"""

LUNG_CT_ENABLEMENTS = [
    Enablement(project_id="lung-ct", application_id=application_id, enabled_by="kim", enabled_at=at(2, 10))
    for application_id in ("jupyterlab", "mitk", "cvat", "collabora")
]

DEPLOY_REQUEST = {
    "application_id": "jupyterlab",
    "version": "4.3.0",
    "name": "jonas-notebook-2",
    "placement": {"scope": "project", "project_id": "lung-ct", "deployed_for": "jonas"},
    "parameters": {"dataFolder": "cohort-a", "gpu": False, "memory": 16},
}

PLATFORM_DEPLOY_REQUEST = {
    "application_id": "collabora",
    "name": "collabora",
    "placement": {"scope": "platform"},
}

UPDATE_REQUEST = {"version": "4.3.0", "parameters": {"memory": 16, "idleHours": None}}

REGISTRATION_REQUEST = {
    "extension": {"id": "jupyterlab-extension", "name": "jupyterlab-extension", "version": "4.3.0"},
    "content": JUPYTERLAB_CONTENT.model_dump(mode="json"),
    "chart_reference": "registry.kaapana.example.org/extensions/jupyterlab-extension:4.3.0",
}
