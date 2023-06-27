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
    def __init__(self, workflow_dir=None, use_minio_mount=None):
        super().__init__(workflow_dir=workflow_dir, use_minio_mount=use_minio_mount)

    @timeit
    def update_data(self, federated_round, tmp_central_site_info):
        # Here the data is collected for a federated learning round
        print(Path(self.fl_working_dir) / str(federated_round))
        print(tmp_central_site_info)
        print(federated_round)

    @timeit
    def on_wait_for_jobs_end(self, federated_round):
        # Here the aggregation takes place
        self.run_in_parallel = True


if __name__ == "__main__":
    # instantiate FederatedTraining class
    kaapana_ft = RadiomicsFederatedTraining(use_minio_mount="/minio")

    kaapana_ft.train()  # calls train method of KaapanaFederatedTrainingBase

    # kaapana_ft.clean_up_minio()  # calls clean_up_minio method of KaapanaFederatedTrainingBase
