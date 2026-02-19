# conftest.py
import logging
import os
import subprocess
from pathlib import Path

import pytest
import pytest_asyncio
import urllib3
from kaapana_test.data import DataEndpoints
from kaapana_test.extensions import ExtensionEndpoints
from kaapana_test.utils.KaapanaPlaywrightDriver import (
    KaapanaPlaywrightDriver,
    ensure_playwright_installed,
)
from kaapana_test.workflows import (
    WorkflowEndpoints,
    collect_all_testcases,
    read_payload_from_yaml,
)

logging.basicConfig(level=logging.INFO)


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
        return subprocess.check_output(["hostname"], text=True).strip()
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
        pytest.skip("Host not available; skipping tests")
    return h


@pytest.fixture(scope="session")
def client_secret(pytestconfig):
    cs = get_client_secret(pytestconfig)
    if not cs:
        pytest.skip("Client secret not available; skipping tests")
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
        pytest.skip("JSON extension parameters not specified; skipping tests")
    return path


@pytest.fixture
def force_download(pytestconfig):
    return pytestconfig.getoption("--force-download", False)


@pytest.fixture
def extension_endpoint(host, client_secret):
    return ExtensionEndpoints(host=host, client_secret=client_secret)


@pytest.fixture
def workflow_endpoint(host, client_secret):
    return WorkflowEndpoints(host=host, client_secret=client_secret)


@pytest.fixture
def data_endpoint(host, client_secret):
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
def generate_extension_tests(metafunc, host, client_secret):
    if not host or not client_secret:
        # Don't fail collection; just parametrize empty
        metafunc.parametrize("extension", [], ids=[])
        return

    try:
        endpoint = ExtensionEndpoints(host=host, client_secret=client_secret)
        extensions = endpoint.get_all_extensions()
        if not extensions:
            metafunc.parametrize("extension", [], ids=[])
            return

        metafunc.parametrize(
            "extension",
            extensions,
            ids=[
                ext.get("chart_name", f"extension_{i}")
                for i, ext in enumerate(extensions)
            ],
        )
    except Exception:
        metafunc.parametrize("extension", [], ids=[])


def generate_dataset_tests(metafunc, source_path: Path):
    if not source_path.exists() or not source_path.is_dir():
        metafunc.parametrize("dataset", [], ids=[])
        return

    logging.info(f"Looking for datasets in: {source_path}")
    datasets = sorted(
        list(source_path.glob("*.tcia")) + list(source_path.glob("*.url"))
    )
    if not datasets:
        metafunc.parametrize("dataset", [], ids=[])
        return

    metafunc.parametrize("dataset", datasets, ids=[d.stem for d in datasets])


def generate_workflow_tests(metafunc, host, client_secret):
    kaapana = WorkflowEndpoints(host=host, client_secret=client_secret)
    if "testconfig" in metafunc.fixturenames:
        files = get_files(metafunc.config)
        test_dir = metafunc.config.getoption("test_dir")

        if files and len(files) != 0:
            testcases = []
            for file in files:
                testcases += read_payload_from_yaml(file)
        elif test_dir:
            testdir = os.path.join(os.getcwd(), test_dir)
            testcases = collect_all_testcases(testdir)
        else:
            testcases = []
            for file in Path(__file__).parents[4].rglob("ci-config/*.yaml"):
                testcases.extend(read_payload_from_yaml(file))

        metafunc.parametrize("testconfig", [(tc, kaapana) for tc in testcases])


def pytest_generate_tests(metafunc):
    host = get_host(metafunc.config)
    client_secret = get_client_secret(metafunc.config)

    if "extension" in metafunc.fixturenames:
        generate_extension_tests(metafunc, host, client_secret)

    if "dataset" in metafunc.fixturenames:
        generate_dataset_tests(
            metafunc, source_path=get_source_directory(metafunc.config)
        )

    if "testconfig" in metafunc.fixturenames:
        generate_workflow_tests(metafunc, host, client_secret)


# ---------------------------------------------------------------------------
# Optional: parametrize test IDs for tuples
# ---------------------------------------------------------------------------
def pytest_make_parametrize_id(config, val, argname):
    if argname == "testconfig" and isinstance(val, tuple):
        testcase, kaapana = val
        return testcase.get("dag_id")
    return None
