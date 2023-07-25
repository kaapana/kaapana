import os
import sys
import psutil
from pathlib import Path
import uuid
import torch
import json
import pickle
import shutil
import collections

sys.path.insert(0, "/")
sys.path.insert(0, "/kaapana/app")
from kaapana_federated.KaapanaFederatedTraining import (
    KaapanaFederatedTrainingBase,
    timeit,
)


class AdvancedCollectMetadataFederatedTraining(KaapanaFederatedTrainingBase):
    def __init__(self, workflow_dir=None, use_minio_mount=None):
        super().__init__(workflow_dir=workflow_dir, use_minio_mount=use_minio_mount)

    @timeit
    def upload_workflow_dir_to_minio_object(
        self, federated_round, tmp_central_site_info
    ):
        # Overwrite base function since no upload back to minio is needed
        pass

    @timeit
    def update_data(self, federated_round, tmp_central_site_info):
        pass


if __name__ == "__main__":
    # instantiate FederatedTraining class
    kaapana_ft = AdvancedCollectMetadataFederatedTraining(use_minio_mount="/minio")

    # actual FL training
    kaapana_ft.train()  # calls train method of KaapanaFederatedTrainingBase

    # don't clean Minio up, since we want to have the results there!
    # kaapana_ft.clean_up_minio()  # calls clean_up_minio method of KaapanaFederatedTrainingBase
