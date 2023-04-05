import time
import requests
import pytest
from tests.util import get_extensions, install_nnunet, delete_nnunet


def test_nnunet_pending():
    # get extensions list
    ext_list = get_extensions()

    # make sure nnunet is in the list
    nnunet = None
    for ext in ext_list:
        if ext["name"] == "nnunet-workflow":
            nnunet = ext
            break
    assert nnunet is not None, f"could not find nnunet-workflow in extensions list {ext_list=}"

    # delete if already installed
    if len(nnunet["available_versions"]["03-22"]["deployments"]) > 0:
        print("########## nnunet already installed")
        delete_nnunet()
        installed = check_nnunet_installed(
            return_on_install=False,
            interval=2,
            iterations=15
        )

    # install
    install_nnunet()
    installed = check_nnunet_installed(
        return_on_install=True,
        interval=2,
        iterations=15
    )
    if installed:
        print("########## uninstalling nnunet before finish...")
        delete_nnunet()


def check_nnunet_installed(
    return_on_install: bool = True,
    interval: int = 2,
    iterations: int = 15
):
    print(f"checking if nnunet is installed every {interval} seconds for {iterations} iterations")

    for i in range(0, iterations):
        time.sleep(interval)
        print("getting extensions... iteration:", i)
        # get extensions list & fetch nnunet
        ext_list = get_extensions()
        nnunet = None
        for ext in ext_list:
            if ext["name"] == "nnunet-workflow":
                nnunet = ext
                break
        assert nnunet is not None, f"could not find nnunet-workflow in extensions list {ext_list}"
        if len(nnunet["available_versions"]["03-22"]["deployments"]) > 0:
            print("nnunet is installed")
            print(nnunet["available_versions"]["03-22"]["deployments"])
            if return_on_install:
                return True
        else:
            print("nnunet is not installed")
            if not return_on_install:
                return False
    raise AssertionError(f"check_nnunet_installed returned None, {return_on_install=}")
