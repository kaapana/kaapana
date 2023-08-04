import requests
import time
from tests.util import get_extensions


def test_file_upload():
    ext_name = "test-workflow"
    ext_fname = "test-workflow-0.0.1.tgz"
    # TODO: delete tgz file from extensions folder initially
    ext_list = get_extensions()
    found = False
    for ext in ext_list:
        if ext["name"] == ext_name:
            found = True
            break
    assert found == False

    url = "http://localhost:5000/file"
    # TODO: change file path if necessary
    file = {"file": open(ext_fname, "rb")}
    r = requests.post(url, files=file)
    assert r.status_code == 200
    print("request returned", r.text)

    time.sleep(1)

    ext_list = get_extensions()
    print(ext_list, len(ext_list))
    found = False
    for ext in ext_list:
        if ext["name"] == ext_name:
            found = True
            break
    assert found == True
