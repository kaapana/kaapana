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

        # new:
        self.run_in_parallel = False

    def tensorboard_logs(self, federated_round):
        pass

    @timeit
    def update_data(
        self, federated_round, tmp_central_site_info
    ):  # is called by KaapanaFederatedTrainingBase's central_steps() method ; method overwrites empty update_data() method of KaapanaFederatedTrainingBase
        print(Path(os.path.join(self.fl_working_dir, str(federated_round))))

        print("Training mode")

        current_federated_round_dir = Path(
            os.path.join(self.fl_working_dir, str(federated_round))
        )
        print(psutil.Process(os.getpid()).memory_info().rss / 1024**2)

        print("Loading averaged checkpoints")
        for idx, fname in enumerate(
            current_federated_round_dir.rglob("model_final_checkpoint.model")
        ):
            print(fname)
            # _sum_state_dicts(fname, idx)
            print(psutil.Process(os.getpid()).memory_info().rss / 1024**2)

        print("Saving averaged checkpoints")
        for idx, fname in enumerate(
            current_federated_round_dir.rglob("model_final_checkpoint.model")
        ):
            print(fname)
            # _save_state_dict(fname, averaged_state_dict)
            print(psutil.Process(os.getpid()).memory_info().rss / 1024**2)

        # in the last federated round save final model to minio
        if (
            self.remote_conf_data["federated_form"]["federated_total_rounds"]
            == federated_round + 1
            and self.use_minio_mount is not None
        ):
            src = (
                current_federated_round_dir
                / self.remote_sites[0]["instance_name"]
                / "fed-packaging-operator"
            )
            dst = os.path.join(
                "/", self.workflow_dir, "advanced_collect_metadata-results"
            )
            print(
                f"Last round! Copying final advanced_collect_metadata files from {src} to {dst}"
            )
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src=src, dst=dst)

    @timeit
    def on_wait_for_jobs_end(self, federated_round):
        print("DEF ON_WAIT_FOR_JOBS_END()")

        self.remote_conf_data["workflow_form"]["train_continue"] = True
        self.run_in_parallel = True

        print(
            federated_round,
            self.remote_conf_data["federated_form"]["federated_total_rounds"],
        )


if __name__ == "__main__":
    # instantiate FederatedTraining class
    kaapana_ft = AdvancedCollectMetadataFederatedTraining(use_minio_mount="/minio")

    # actual FL training
    kaapana_ft.train()  # calls train method of KaapanaFederatedTrainingBase

    kaapana_ft.clean_up_minio()  # calls clean_up_minio method of KaapanaFederatedTrainingBase
