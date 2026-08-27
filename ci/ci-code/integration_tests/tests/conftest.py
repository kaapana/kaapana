# conftest.py
import logging
import os
import subprocess
from pathlib import Path

import pytest
import pytest_asyncio
import urllib3
from integration_tests.data import DataEndpoints, clone_test_data_repos
from integration_tests.extensions import ExtensionEndpoints
from integration_tests.utils.KaapanaPlaywrightDriver import (
    KaapanaPlaywrightDriver,
    ensure_playwright_installed,
)
from integration_tests.workflows import (
    WorkflowEndpoints,
    collect_testcase_files,
    plan_testcases,
)

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pytest CLI options
# ---------------------------------------------------------------------------
def pytest_addoption(parser):
    parser.addoption(
        "--ip-address", default=None, action="store", help="IP address to scan"
    )
    parser.addoption("--host", default=None, help="Host URL of the Kaapana instance")
    parser.addoption(
        "--client-secret", default=None, help="Client secret for Kaapana instance"
    )
    parser.addoption(
        "--allowed-ports",
        default="22,80,443,6443,9000,9001",
        help="Comma-separated allowed ports",
    )
    parser.addoption(
        "--json-extension-params",
        default=None,
        help="JSON file with extension parameters",
    )
    parser.addoption(
        "--timeout", type=int, default=300, help="Timeout for long operations"
    )
    parser.addoption(
        "--source-directory", default=None, help="Directory containing dataset files"
    )
    parser.addoption(
        "--download-directory", default=None, help="Directory to download datasets"
    )
    parser.addoption(
        "--force-download", action="store_true", help="Force dataset re-download"
    )
    parser.addoption(
        "--test-data-repo-dir",
        action="append",
        default=None,
        help="Directory of <dataset>/<series-uid>.zip archives, skips cloning. Repeat for several.",
    )
    parser.addoption(
        "--test-data-repo-root",
        default=None,
        help="Where CI_TEST_DATA_REPOS is cloned. Defaults next to --download-directory; "
        "CI points it at a host volume shared by every job on the runner.",
    )
    parser.addoption(
        "--files", nargs="*", default=None, help="Specific test files to collect"
    )
    parser.addoption(
        "--test-dir", default=None, help="Specific test directories to collect"
    )


# ---------------------------------------------------------------------------
# Auto-detect helpers
# ---------------------------------------------------------------------------
def auto_host():
    try:
        return subprocess.check_output(
            ["hostname", "-I", "|", "awk", "'{print $1}'"], text=True
        ).strip()
    except Exception:
        return None


def auto_client_secret():
    try:
        cmd = "helm get values kaapana-admin-chart -o json | jq -r .global.oidc_client_secret"
        return subprocess.check_output(["bash", "-lc", cmd], text=True).strip()
    except Exception:
        return None


def get_host(config):
    # CLI → ENV → fallback
    return config.getoption("--host") or os.getenv("HOST") or auto_host()


def get_client_secret(config):
    # CLI → ENV → fallback
    return (
        config.getoption("--client-secret")
        or os.getenv("CLIENT_SECRET")
        or auto_client_secret()
    )


def get_timeout(config):
    return config.getoption("--timeout") or int(os.getenv("TIMEOUT", 300))


def get_allowed_ports(config):
    val = config.getoption("--allowed-ports") or os.getenv("ALLOWED_PORTS")
    return [p.strip() for p in val.split(",")] if val else []


def get_source_directory(config) -> Path:
    return Path(
        config.getoption("--source-directory")
        or os.getenv("SOURCE_DIRECTORY")
        or (Path(__file__).parent.parent / "data" / "download-info").resolve()
    )


def get_download_directory(config) -> Path:
    return Path(
        config.getoption("--download-directory")
        or os.getenv("DOWNLOAD_DIRECTORY")
        or (Path(__file__).parent.parent / "data" / "download-file").resolve()
    )


def get_test_data_repo_root(config) -> Path:
    """
    Where the test-data repositories are cloned. A clone here is reused by
    every later job that sees the same directory, so pointing this at a
    persistent volume is what keeps the data off the network.
    """
    return Path(
        config.getoption("--test-data-repo-root")
        or os.getenv("CI_TEST_DATA_REPO_ROOT")
        or get_download_directory(config).parent
    )


def get_test_data_repo_dirs(config) -> list:
    """
    Directories holding the test series, in the order to try them.

    --test-data-repo-dir points at directories that already exist. Otherwise
    CI_TEST_DATA_REPOS is cloned into --test-data-repo-root, a JSON array of
    {url, token, ref, path} or a path to a file holding one. Neither set means
    TCIA only.
    """
    if flags := config.getoption("--test-data-repo-dir"):
        return list(flags)
    if spec := os.getenv("CI_TEST_DATA_REPOS"):
        return clone_test_data_repos(spec, get_test_data_repo_root(config))
    return []


def get_json_extension_params(config):
    return (
        config.getoption("--json-extension-params")
        or os.getenv("JSON_EXTENSION_PARAMS")
        or (Path(__file__).parent.parent / "data" / "extension_params.json").resolve()
    )


def get_files(config):
    return (
        config.getoption("--files")
        or os.getenv("FILES")
        or list(Path(__file__).parents[4].glob("**/ci-config.yaml"))
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def host(pytestconfig):
    h = get_host(pytestconfig)
    if not h:
        pytest.fail("Host not provided; failing tests")
    return h


@pytest.fixture(scope="session")
def client_secret(pytestconfig):
    cs = get_client_secret(pytestconfig)
    if not cs:
        pytest.fail("Client secret not provided; failing tests")
    return cs


@pytest.fixture(scope="session")
def ip_address(pytestconfig):
    return (
        pytestconfig.getoption("--ip-address") or os.getenv("IP_ADDRESS") or "127.0.0.1"
    )


@pytest.fixture(scope="session")
def timeout(pytestconfig):
    return get_timeout(pytestconfig)


@pytest.fixture(scope="session")
def allowed_ports(pytestconfig):
    return get_allowed_ports(pytestconfig)


@pytest.fixture(scope="session")
def download_directory(pytestconfig):
    return get_download_directory(pytestconfig)


@pytest.fixture(scope="session")
def json_extension_params(pytestconfig):
    path = get_json_extension_params(pytestconfig)
    if not path:
        pytest.fail("JSON extension parameters not specified; failing tests")
    return path


@pytest.fixture
def force_download(pytestconfig):
    return pytestconfig.getoption("--force-download", False)


@pytest.fixture(scope="session")
def test_data_repo_dirs(pytestconfig):
    dirs = get_test_data_repo_dirs(pytestconfig)
    missing = [d for d in dirs if not Path(d).is_dir()]
    if missing:
        logging.warning("Configured test-data repositories do not exist: %s", missing)
    return dirs


@pytest.fixture(scope="session")
def extension_endpoints(host, client_secret):
    return ExtensionEndpoints(host=host, client_secret=client_secret)


@pytest.fixture(scope="session")
def workflow_endpoints(host, client_secret):
    return WorkflowEndpoints(host=host, client_secret=client_secret)


@pytest.fixture(scope="session")
def data_endpoints(host, client_secret):
    return DataEndpoints(host=host, client_secret=client_secret)


@pytest_asyncio.fixture
async def driver():
    await ensure_playwright_installed()
    drv = await KaapanaPlaywrightDriver(headless=True).start_driver()
    yield drv
    await drv.quit()


@pytest.fixture(autouse=True, scope="session")
def disable_insecure_request_warning():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ---------------------------------------------------------------------------
# Dynamic test generation
# ---------------------------------------------------------------------------
def generate_extension_tests(metafunc):
    client_secret = get_client_secret(metafunc.config)
    host = get_host(metafunc.config)
    endpoint = ExtensionEndpoints(host=host, client_secret=client_secret)

    try:
        extensions = endpoint.get_all_extensions()
    except Exception as e:
        pytest.fail(f"Failed to fetch extensions during collection: {e}")

    if not extensions:
        pytest.fail("No extensions found")

    metafunc.parametrize(
        "extension", extensions, ids=[ext["chart_name"] for ext in extensions]
    )


def generate_dataset_tests(metafunc):
    source_path: Path = get_source_directory(metafunc.config)
    if not source_path.exists() or not source_path.is_dir():
        pytest.fail("No source directory found.")
        return

    logging.info(f"Looking for datasets in: {source_path}")
    datasets = sorted(
        list(source_path.glob("*.tcia")) + list(source_path.glob("*.url"))
    )
    if not datasets:
        pytest.fail("No dataset found.")
        return

    metafunc.parametrize("dataset", datasets, ids=[d.stem for d in datasets])


def generate_workflow_tests(metafunc):
    files = get_files(metafunc.config)
    test_dir = metafunc.config.getoption("test_dir")

    if files and len(files) != 0:
        testcase_files = [Path(file) for file in files]
    elif test_dir:
        testcase_files = collect_testcase_files(os.path.join(os.getcwd(), test_dir))
    else:
        testcase_files = sorted(Path(__file__).parents[4].rglob("ci-config/*.yaml"))

    try:
        planned = plan_testcases(testcase_files)
    except ValueError as invalid_declaration:
        raise pytest.UsageError(str(invalid_declaration)) from None

    if any(case.after for case in planned) and not _distribution_keeps_groups(
        metafunc.config
    ):
        raise pytest.UsageError(
            "testcases declare ci_after, which needs --dist loadgroup to keep a group "
            "on one worker"
        )

    params = []
    ids = []
    for case in planned:
        marks = [pytest.mark.xdist_group(case.group)]
        if case.step or case.after:
            marks.append(pytest.mark.ci_step(case.step, case.after))
        params.append(pytest.param(case.payload, marks=marks))
        ids.append(case.payload.get("dag_id"))

    metafunc.parametrize("testconfig", params, ids=ids)


def pytest_generate_tests(metafunc):
    host = get_host(metafunc.config)
    client_secret = get_client_secret(metafunc.config)

    if not host:
        pytest.fail("No host specified")

    if not client_secret:
        pytest.fail("No client_secret specified")

    if "extension" in metafunc.fixturenames:
        generate_extension_tests(metafunc)

    if "dataset" in metafunc.fixturenames:
        generate_dataset_tests(metafunc)

    if "testconfig" in metafunc.fixturenames:
        generate_workflow_tests(metafunc)


# ---------------------------------------------------------------------------
# Declared testcase dependencies (ci_step / ci_after)
# ---------------------------------------------------------------------------
# Outcome of every ci_step this process ran. Members of one xdist group always
# land on the same worker, so a process local record is enough to verify the
# declared prerequisites instead of trusting the order of the distribution,
# which loadgroup does not promise.
_step_outcomes: dict[str, str] = {}


def _distribution_keeps_groups(config) -> bool:
    """
    Whether a group of testcases is kept together by the current distribution.
    """
    if hasattr(config, "workerinput"):
        # xdist resets its own options inside the worker and leaves this flag behind
        return config.option.loadgroup
    return not config.option.numprocesses or config.option.dist == "loadgroup"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "ci_step(name, after): name of a workflow testcase and the names it follows",
    )


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    marker = item.get_closest_marker("ci_step")
    if report.when == "call" and marker and marker.args[0]:
        _step_outcomes[marker.args[0]] = report.outcome
    return report


@pytest.fixture(autouse=True)
def declared_prerequisites(request):
    """
    Fail a testcase whose declared prerequisites did not succeed before it.
    """
    marker = request.node.get_closest_marker("ci_step")
    if not marker:
        return
    for prerequisite in marker.args[1]:
        outcome = _step_outcomes.get(prerequisite, "did not run")
        if outcome != "passed":
            pytest.fail(
                f"prerequisite {prerequisite!r} {outcome} on this worker, so the state "
                f"this testcase expects was never established"
            )
