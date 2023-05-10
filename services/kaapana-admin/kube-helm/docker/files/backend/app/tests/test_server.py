import requests
from tests.util import get_extensions


def test_health_check():
    r = requests.get("http://localhost:5000/health-check")
    assert (
        r.text == "Kube-Helm api is up and running!"
    ), f"failed to get right response from /health-check, '{r.text}'"
    assert (
        str(r.status_code)[0] == "2"
    ), f"health-check did not respond with right status code, got {r.status_code} instead"


def test_extensions_list():
    _ = get_extensions()
