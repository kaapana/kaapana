import pytest
import urllib3
import logging

logging.basicConfig(level=logging.INFO)


def pytest_addoption(parser):
    parser.addoption(
        "--test-dir",
        help="Directory of files with testcases",
        default="integration_tests/testcases/",
    )
    parser.addoption("--host", default=None, help="Host URL of the Kaapana instance.")
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


def pytest_make_parametrize_id(config, val, argname):
    if argname == "testconfig" and isinstance(val, tuple):
        testcase, host, client_secret = val
        return testcase.get("dag_id")
    return None


@pytest.fixture(autouse=True, scope="session")
def disable_insecure_request_warning():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
