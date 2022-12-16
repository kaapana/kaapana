import requests
import schemas


def get_extensions():
    resp = requests.get("http://localhost:5000/extensions")
    ext_list = resp.json()
    # assert len(ext_list) == 18, "number of extensions is expected to be 18, not {0}".format(len(ext_list))
    for ext in ext_list:
        _ = schemas.KaapanaExtension.parse_obj(ext)
    return ext_list


def install_nnunet():
    print("########## installing nnunet...")
    rinstall = requests.post("http://localhost:5000/helm-install-chart", json={
        "name": "nnunet-workflow",
        "version": "03-22",
        "keywords": ["kaapanaworkflow"]
    })
    assert str(rinstall.status_code)[0] == "2", "/helm-install-chart did not respond with right status code, got {0} instead".format(rinstall.status_code)
    print(rinstall.text)


def delete_nnunet():
    print("########## deleting nnunet...")
    rdel = requests.post("http://localhost:5000/helm-delete-chart", json={
        "helm_command_addons": "",
        "release_name": "nnunet-workflow",
        "release_version": "03-22"
    })
    assert str(rdel.status_code)[0] == "2", "/helm-delete-chart did not respond with right status code, got {0} instead".format(rdel.status_code)
    assert rdel.text == "Successfully uninstalled nnunet-workflow", "/helm-delete-chart returned different response {0}".format(rdel.text)
