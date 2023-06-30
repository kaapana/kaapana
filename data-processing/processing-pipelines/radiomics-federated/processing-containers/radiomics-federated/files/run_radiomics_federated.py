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


class RadiomicsFederatedTraining(KaapanaFederatedTrainingBase):
    def __init__(self):
        super().__init__()

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
    kaapana_ft = RadiomicsFederatedTraining()
    kaapana_ft.train()  # calls train method of KaapanaFederatedTrainingBase
    kaapana_ft.clean_up_minio()  # calls clean_up_minio method of KaapanaFederatedTrainingBase
