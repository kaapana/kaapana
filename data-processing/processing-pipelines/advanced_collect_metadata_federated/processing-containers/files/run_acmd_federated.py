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

        # removed starting from recovery mode, and ValueError
        # self.remote_conf_data['workflow_form']['epochs_per_round'] = int(self.remote_conf_data['workflow_form']['train_max_epochs'] / self.remote_conf_data['federated_form']['federated_total_rounds'])  # take 'num_epochs' of dag_breast_density_classification instead of 'train_max_epochs'
        # self.remote_conf_data['workflow_form']['epochs_per_round'] = self.remote_conf_data['workflow_form']['num_epochs']

        # print(f"Overwriting prep_increment_step to to_dataset_properties!")
        # self.remote_conf_data['workflow_form']['prep_increment_step'] = 'to_dataset_properties'

        # # We increase the total federated round by one, because we need the final round to download the final model.
        # self.remote_conf_data['federated_form']['federated_total_rounds'] = self.remote_conf_data['federated_form']['federated_total_rounds'] + 1
        # print(f"Epochs per round {self.remote_conf_data['workflow_form']['epochs_per_round']}")

    def tensorboard_logs(self, federated_round):
        pass

    @timeit
    def update_data(
        self, federated_round, tmp_central_site_info
    ):  # is called by KaapanaFederatedTrainingBase's central_steps() method ; method overwrites empty update_data() method of KaapanaFederatedTrainingBase
        print(Path(os.path.join(self.fl_working_dir, str(federated_round))))

        # if federated_round == -1:   # changed -2 to -1 due to having only 1 preprocessing round
        #     print('Preprocessing round!')

        #     # removed preprocessing regarding dataset properties

        #     # Dummy creation of bdc-training folder, because a tar is expected in the next round due
        #     # to from_previous_dag_run not None. Mybe there is a better solution for the future...
        #     # for instance_name, tmp_site_info in tmp_central_site_info.items():
        #     #     bdc_training_file_path = tmp_site_info['file_paths'][0].replace('bdc-preprocess', 'bdc-training')
        #     #     bdc_training_dir = bdc_training_file_path.replace('.tar', '')
        #     #     Path(bdc_training_dir).mkdir(exist_ok=True)
        #     #     tmp_site_info['file_paths'].append(bdc_training_file_path)
        #     #     bdc_training_next_object_name = tmp_site_info['next_object_names'][0].replace('bdc-preprocess', 'bdc-training')
        #     #     tmp_site_info['next_object_names'].append(bdc_training_next_object_name)
        # else:
        print("Training mode")

        # if federated_round >= 0:
        #     self.tensorboard_logs(federated_round)

        current_federated_round_dir = Path(
            os.path.join(self.fl_working_dir, str(federated_round))
        )
        print(psutil.Process(os.getpid()).memory_info().rss / 1024**2)

        # Not 100% sure if it is necessary to put those into functions, I did this to be sure to not allocated unnecssary memory...
        # def _sum_state_dicts(fname, idx):
        #     checkpoint = torch.load(fname, map_location=torch.device('cpu'))
        #     if idx==0:
        #         sum_state_dict = checkpoint['state_dict']
        #     else:
        #         sum_state_dict = torch.load('tmp_state_dict.pt')
        #         for key, value in checkpoint['state_dict'].items():
        #             sum_state_dict[key] =  sum_state_dict[key] + checkpoint['state_dict'][key]
        #     torch.save(sum_state_dict, 'tmp_state_dict.pt')

        # def _save_state_dict(fname, averaged_state_dict):
        #     checkpoint = torch.load(fname, map_location=torch.device('cpu'))
        #     checkpoint['state_dict'] = averaged_state_dict
        #     torch.save(checkpoint, fname)

        print("Loading averaged checkpoints")
        for idx, fname in enumerate(
            current_federated_round_dir.rglob("model_final_checkpoint.model")
        ):
            print(fname)
            # _sum_state_dicts(fname, idx)
            print(psutil.Process(os.getpid()).memory_info().rss / 1024**2)

        # sum_state_dict = torch.load('tmp_state_dict.pt')
        # os.remove("tmp_state_dict.pt")

        # averaged_state_dict = collections.OrderedDict()
        # for key, value in sum_state_dict.items():
        #     averaged_state_dict[key] = sum_state_dict[key] / (idx+1.)   # is this the actual averaging of the FL Aggregation?

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
                / "advanced_collect_metadata"
            )
            dst = os.path.join("/", self.workflow_dir, "advanced_collect_metadata")
            print(
                f"Last round! Copying final advanced_collect_metadata files from {src} to {dst}"
            )
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src=src, dst=dst)
            # shutil.copyfile(src=os.path.join(os.path.dirname(fname), 'dataset.json'), dst=os.path.join(dst, 'dataset.json')) # A little bit ugly... but necessary for Bin2Dcm operator

    @timeit
    def on_wait_for_jobs_end(
        self, federated_round
    ):  # called by KaapanaFederatedTrainingBase's method train_step()
        # method to modify list of skip_operators after each federated_round
        # if federated_round == -1:
        #     print('Taking actions ...')

        #     print('Removing breast_density_classifier from skip_operators')
        #     self.remote_conf_data['federated_form']['skip_operators'].remove('breast_density_classifier')
        #     # self.remote_conf_data['federated_form']['skip_operators'] = [e for e in self.remote_conf_data['federated_form']['skip_operators'] if e not in ('get_from_minio_split', 'breast_density_classifier')]

        #     print('Adding get-input-data, get_from_minio_init, train_val_split to skip_operators')
        #     self.remote_conf_data['federated_form']['skip_operators'] = self.remote_conf_data['federated_form']['skip_operators'] + ['get-input-data', 'get_from_minio_init', 'train_val_datasplit']
        # if federated_round == 0:
        #     print('Adding get-input-data, get_from_minio_init to skip_operators')
        #     self.remote_conf_data['federated_form']['skip_operators'] = self.remote_conf_data['federated_form']['skip_operators'] + ['get-input-data', 'get_from_minio_init']   # , 'train_val_datasplit'
        # else:
        print("DEF ON_WAIT_FOR_JOBS_END()")

        self.remote_conf_data["workflow_form"]["train_continue"] = True
        self.run_in_parallel = True

        print(
            federated_round,
            self.remote_conf_data["federated_form"]["federated_total_rounds"],
        )


if __name__ == "__main__":
    kaapana_ft = AdvancedCollectMetadataFederatedTraining(
        use_minio_mount="/minio"
    )  # instantiate FederatedTraining class

    # preprocess workflow
    # kaapana_ft.train_step(-1)   # calls train_step method of KaapanaFederatedTrainingBase
    # actual FL training
    kaapana_ft.train()  # calls train method of KaapanaFederatedTrainingBase

    kaapana_ft.clean_up_minio()  # calls clean_up_minio method of KaapanaFederatedTrainingBase
