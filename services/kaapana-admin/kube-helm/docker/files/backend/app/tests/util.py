import requests
import schemas


def get_extensions():
    resp = requests.get("http://localhost:5000/extensions")
    ext_list = resp.json()
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
    assert str(rinstall.status_code)[0] == "2", f"/helm-install-chart did not respond with right status code, got {rinstall.status_code} instead"
    print(rinstall.text)


def delete_nnunet():
    print("########## deleting nnunet...")
    rdel = requests.post("http://localhost:5000/helm-delete-chart", json={
        "helm_command_addons": "",
        "release_name": "nnunet-workflow",
        "release_version": "03-22"
    })
    assert str(rdel.status_code)[0] == "2", f"/helm-delete-chart did not respond with right status code, got {rdel.status_code} instead"
    assert rdel.text == "Successfully uninstalled nnunet-workflow", f"/helm-delete-chart returned different response {rdel.text}"
