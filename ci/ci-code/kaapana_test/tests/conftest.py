# conftest.py
import logging
from pathlib import Path

import pytest
import pytest_asyncio
import urllib3
from kaapana_test.extensions.utils_extensions import ExtensionEndpoint
from kaapana_test.utils.kaapana_playwright_driver_async import (
    KaapanaPlaywrightDriverAsync,
    ensure_playwright_installed_async,
)

logging.basicConfig(level=logging.INFO)


@pytest.fixture(scope="session")
def host(pytestconfig):
    """Host of Kaapana deployment"""
    value = pytestconfig.getoption("--host")
    if not value:
        pytest.exit("Missing --host argument", returncode=2)
    return value


@pytest.fixture(scope="session")
def client_secret(pytestconfig):
    return pytestconfig.getoption("--client-secret")


@pytest.fixture
def extension_endpoint(host, client_secret):
    """Provide a configured ExtensionEndpoint instance."""
    return ExtensionEndpoint(host=host, client_secret=client_secret)


@pytest_asyncio.fixture
async def driver():
    """Async Playwright driver fixture."""
    await ensure_playwright_installed_async()
    drv = await KaapanaPlaywrightDriverAsync(headless=True).start_driver()
    yield drv
    await drv.quit()


def pytest_addoption(parser):
    parser.addoption("--ip-address", action="store", help="IP address to scan")
    parser.addoption(
        "--allowed-ports", action="store", help="Comma-separated allowed ports"
    )
    parser.addoption("--host", default=None, help="Host URL of the Kaapana instance.")

    parser.addoption(
        "--test-dir",
        help="Directory of files with testcases",
        default="integration_tests/testcases/",
    )

    parser.addoption(
        "--files",
        help="Collect testcases from a list of files instead of test_directory",
        nargs="*",
    )
    parser.addoption(
        "--client-secret",
        default=None,
        help="The client secret of the kaapana client in keycloak.",
    )
    parser.addoption(
        "--json-extension-params",
        help="Path to a json file containing extension specific parameters. The json has to be a dict, where the keys are the chart_names of the extensions and the values are dicts with the extension parameters.",
    )
    parser.addoption(
        "--timeout",
        type=int,
        default=300,
    )
    parser.addoption(
        "--source-directory",
        default=None,
        help="Directory containing dataset files (.tcia or .url) to be used in test_send_data.",
    )
    parser.addoption(
        "--download-directory",
        help="Directory where datasets will be downloaded during test_send_data. If not specified, a temporary directory will be used.",
    )

    parser.addoption(
        "--force-download",
        action="store_true",
        help="Force re-download of datasets in test_send_data even if they already exist in the download directory.",
    )


def pytest_make_parametrize_id(config, val, argname):
    if argname == "testconfig" and isinstance(val, tuple):
        testcase, kaapana = val
        return testcase.get("dag_id")
    return None


@pytest.fixture(scope="session")
def json_extension_params(pytestconfig):
    """Path to JSON file containing extension parameters"""
    path = pytestconfig.getoption("--json-extension-params")
    if not path:
        pytest.exit("Missing --json-extension-params argument", returncode=2)
    return path


@pytest.fixture
def timeout(request):
    return request.config.getoption("--timeout")


@pytest.fixture
def ip_address(request):
    return request.config.getoption("--ip-address")


@pytest.fixture
def allowed_ports(request):
    allowed = request.config.getoption("--allowed-ports")
    return [p.strip() for p in allowed.split(",")] if allowed else []


@pytest.fixture
def source_directory(pytestconfig):
    return pytestconfig.getoption("--source-directory")


@pytest.fixture
def download_directory(pytestconfig):
    return pytestconfig.getoption("--download-directory")


@pytest.fixture
def force_download(pytestconfig):
    return pytestconfig.getoption("--force-download", False)


@pytest.fixture(autouse=True, scope="session")
def disable_insecure_request_warning():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def pytest_generate_tests(metafunc):
    """Dynamically parametrize extension tests."""
    if "extension" in metafunc.fixturenames:
        # Get host and client_secret from command line options
        host = metafunc.config.getoption("--host")
        client_secret = metafunc.config.getoption("--client-secret")

        if not host:
            pytest.exit("Missing --host argument", returncode=2)

        # Create a temporary ExtensionEndpoint to get extensions
        from kaapana_test.extensions.utils_extensions import ExtensionEndpoint

        endpoint = ExtensionEndpoint(host=host, client_secret=client_secret)

        try:
            extensions = endpoint.get_all_extensions()
            if not extensions:
                pytest.exit("No extensions found", returncode=1)

            # Parametrize with extension data
            metafunc.parametrize(
                "extension",
                extensions,
                ids=[
                    ext.get("chart_name", f"extension_{i}")
                    for i, ext in enumerate(extensions)
                ],
            )
        except Exception as e:
            pytest.exit(f"Failed to get extensions: {e}", returncode=1)

    if "dataset" in metafunc.fixturenames:
        source_dir = metafunc.config.getoption("--source-directory")
        source_path = Path(source_dir)

        if not source_path.exists() or not source_path.is_dir():
            pytest.exit(f"Dataset directory not found: {source_path}", returncode=2)

        # Discover all .tcia and .url datasets
        datasets = sorted(
            list(source_path.glob("*.tcia")) + list(source_path.glob("*.url"))
        )

        if not datasets:
            pytest.exit(f"No datasets found in: {source_path}", returncode=1)

        # Parameterize the test with each dataset file
        metafunc.parametrize("dataset", datasets, ids=[d.stem for d in datasets])
