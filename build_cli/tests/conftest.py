import pytest

# build_cli.build must be imported before the other build_cli packages, as in cli.py.
# Its helpers import these packages, and they import build_cli.build back.
from build_cli.build import BuildConfig, BuildHelper, BuildState, IssueTracker
from build_cli.container import ContainerHelper
from build_cli.extension import ExtensionHelper
from build_cli.helm import HelmChartHelper

HELPERS = (BuildHelper, ContainerHelper, ExtensionHelper, HelmChartHelper)


@pytest.fixture
def kaapana_dir(tmp_path):
    (tmp_path / "data-processing" / "workflows").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def build_config(kaapana_dir):
    return BuildConfig.model_construct(
        kaapana_dir=kaapana_dir,
        build_dir=kaapana_dir / "build",
        default_registry="registry.example.com/kaapana",
        build_ignore_patterns=[],
        lint_only=False,
        interactive=False,
        containers_to_build=[],
        containers_to_build_by_charts=[],
    )


@pytest.fixture
def build_state():
    return BuildState(started_at=0.0)


@pytest.fixture(autouse=True)
def helpers(build_config, build_state):
    # The helpers keep their state in class attributes, and init() only sets it once.
    for helper in HELPERS:
        helper._build_config = build_config
        helper._build_state = build_state
    IssueTracker.issues = []
    IssueTracker.exit_on_error = False
    yield
    for helper in HELPERS:
        helper._build_config = None
        helper._build_state = None
    IssueTracker.issues = []
