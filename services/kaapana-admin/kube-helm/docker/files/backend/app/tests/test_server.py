import requests
from tests.util import get_extensions

def test_health_check():
    r = requests.get("http://localhost:5000/health-check")
    assert r.text == "Kube-Helm api is up and running!", "failed to get right response from /health-check, '{0}'".format(r.text)
    assert str(r.status_code)[0] == "2", "health-check did not respond with right status code, got {0} instead".format(r.status_code)


def test_extensions_list():
    _ = get_extensions()

