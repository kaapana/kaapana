import requests
import time
from tests.util import get_extensions


def test_file_upload():
    fname = "test-container.tar"

    url = "http://localhost:5000/file_chunks"
    # TODO: change file path if necessary
    print("opening file...")
    file = {"file": open("tests/" + fname, "rb")}
    print("file opened")
    try:
        r = requests.post(url, files=file)
    except Exception as e:
        print("err", e)
        return

    assert r.status_code == 200
    print("request returned:", r.text)
