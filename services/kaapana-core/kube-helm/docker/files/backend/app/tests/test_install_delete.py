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
    assert nnunet is not None, "could not find nnunet-workflow in extensions list {0}".format(ext_list)

    # delete if already installed
    if len(nnunet["available_versions"]["03-22"]["deployments"]) > 0:
        print("nnunet already installed")
        delete_nnunet()
        print("sleeping for 30 seconds...")
        time.sleep(30)
        deleted = False
        while not deleted:
            ext_list = get_extensions()
            for ext in ext_list:
                if ext["name"] == "nnunet-workflow":
                    nnunet = ext
                    break
            assert nnunet is not None, "could not find nnunet-workflow in extensions list {0}".format(ext_list)
            if len(nnunet["available_versions"]["03-22"]["deployments"]) > 0:
                print("nnunet still installed, sleeping 5 more seconds")
                time.sleep(5)
            else:
                print("nnunet is uninstalled")
                break

    # install
    install_nnunet()

    # get extensions list every 2 seconds
    for i in range(0, 15):
        time.sleep(2)
        print("getting extensions... ", i)
        # get extensions list & fetch nnunet
        ext_list = get_extensions()
        nnunet = None
        for ext in ext_list:
            if ext["name"] == "nnunet-workflow":
                nnunet = ext
                break
        assert nnunet is not None, "could not find nnunet-workflow in extensions list {0}".format(ext_list)
        if len(nnunet["available_versions"]["03-22"]["deployments"]) > 0:
            print("nnunet installed, uninstalling before finish...")
            delete_nnunet()
            break
        else:
            print("nnunet not installed")


