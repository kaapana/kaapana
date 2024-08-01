import os
import sys
from pathlib import Path
from multiprocessing import Pool
import torch
import json
import pickle
import shutil
import collections
from collections import OrderedDict
from torch.utils.tensorboard import SummaryWriter
from nnunet.training.model_restore import restore_model
from nnunet.experiment_planning.DatasetAnalyzer import DatasetAnalyzer
from batchgenerators.utilities.file_and_folder_operations import join
import psutil
import numpy as np

sys.path.insert(0, "/")
sys.path.insert(0, "/kaapana/app")
from kaapana_federated.KaapanaFederatedTraining import (
    KaapanaFederatedTrainingBase,
    timeit,
)


class nnUNetFederatedTraining(KaapanaFederatedTrainingBase):
    @staticmethod
    def get_network_trainer(folder):
        checkpoint = join(folder, "model_final_checkpoint.model")
        pkl_file = checkpoint + ".pkl"
        return restore_model(pkl_file, checkpoint, False)

    # https://github.com/MIC-DKFZ/nnUNet/blob/a7d1d875e8fc3f4e93ca7b51b1ba206711844d92/nnunet/experiment_planning/DatasetAnalyzer.py#L181
    @staticmethod
    def collect_intensity_properties(v_per_mod, num_processes=8):
        num_modalities = len(v_per_mod)
        p = Pool(num_processes)

        results = OrderedDict()
        for mod_id in range(num_modalities):
            results[mod_id] = OrderedDict()
            w = []
            for iv in v_per_mod[str(mod_id)]:
                w += iv

            # (
            #     median,
            #     mean,
            #     sd,
            #     mn,
            #     mx,
            #     percentile_99_5,
            #     percentile_00_5,
            # ) = DatasetAnalyzer._compute_stats(w)

            # results[mod_id]["median"] = median
            # results[mod_id]["mean"] = mean
            # results[mod_id]["sd"] = sd
            # results[mod_id]["mn"] = mn
            # results[mod_id]["mx"] = mx
            # results[mod_id]["percentile_99_5"] = percentile_99_5
            # results[mod_id]["percentile_00_5"] = percentile_00_5

            percentiles = np.array((0.5, 50.0, 99.5))
            percentile_00_5, median, percentile_99_5 = np.percentile(w, percentiles)
            results[mod_id]["median"] = median
            results[mod_id]["mean"] = float(np.mean(w))
            results[mod_id]["sd"] = float(np.std(w))
            results[mod_id]["mn"] = float(np.min(w))
            results[mod_id]["mx"] = float(np.max(w))
            results[mod_id]["percentile_99_5"] = percentile_99_5
            results[mod_id]["percentile_00_5"] = percentile_00_5

        p.close()
        p.join()
        return results

    def __init__(self, workflow_dir=None):
        super().__init__(workflow_dir=workflow_dir)

        if (
            "federated_round" in self.remote_conf_data["federated_form"]
            and self.remote_conf_data["federated_form"]["federated_round"] > -1
        ):
            print(
                "Removing one federated_total_rounds since since we are running in recovery mode!"
            )
            self.remote_conf_data["federated_form"]["federated_total_rounds"] = (
                self.remote_conf_data["federated_form"]["federated_total_rounds"] - 1
            )
        if (
            self.remote_conf_data["workflow_form"]["train_max_epochs"]
            % self.remote_conf_data["federated_form"]["federated_total_rounds"]
            != 0
        ):
            raise ValueError(
                "train_max_epochs has to be multiple of federated_total_rounds"
            )
        else:
            self.remote_conf_data["workflow_form"]["epochs_per_round"] = int(
                self.remote_conf_data["workflow_form"]["train_max_epochs"]
                / self.remote_conf_data["federated_form"]["federated_total_rounds"]
            )
        print(f"Overwriting prep_increment_step to to_dataset_properties!")

        self.remote_conf_data["workflow_form"][
            "prep_increment_step"
        ] = "to_dataset_properties"
        # We increase the total federated round by one, because we need the final round to download the final model.
        # The nnUNet won't train an epoch longer, since its train_max_epochs!
        self.remote_conf_data["federated_form"]["federated_total_rounds"] = (
            self.remote_conf_data["federated_form"]["federated_total_rounds"] + 1
        )
        print(
            f"Epochs per round {self.remote_conf_data['workflow_form']['epochs_per_round']}"
        )

    def tensorboard_logs(self, federated_round):
        current_federated_round_dir = Path(
            os.path.join(self.fl_working_dir, str(federated_round))
        )
        for site_info in self.remote_sites:
            filename = (
                current_federated_round_dir
                / site_info["instance_name"]
                / "nnunet-training"
                / "experiment_results.json"
            )
            with open(filename) as json_file:
                workflow_data = json.load(json_file)
            tensorboard_log_dir = Path(
                os.path.join(
                    "/minio",
                    "tensorboard",
                    self.remote_conf_data["federated_form"]["federated_dir"],
                    os.getenv("OPERATOR_OUT_DIR", "federated-operator"),
                    site_info["instance_name"],
                )
            )
            if tensorboard_log_dir.is_dir():
                print("Removing previous logs, since we will write all logs again...")
                shutil.rmtree(tensorboard_log_dir)
            self.writer = SummaryWriter(log_dir=tensorboard_log_dir)
            for epoch_data in workflow_data:
                for key, value in epoch_data.items():
                    if key != "epoch" and key != "fold":
                        self.writer.add_scalar(key, value, epoch_data["epoch"])

    @timeit
    def update_data(self, federated_round, tmp_central_site_info):
        print(Path(os.path.join(self.fl_working_dir, str(federated_round))))

        if federated_round == -2:
            print("Preprocessing round!")
            preprocessing_path = Path(
                os.path.join(self.fl_working_dir, str(federated_round))
            )
            voxels_in_foreground = {}
            dataset_fingerprints_files = []
            for idx, fname in enumerate(
                preprocessing_path.rglob("dataset_fingerprint.json")
            ):
                if "nnUNet_preprocessed" in str(fname):
                    dataset_fingerprints_files.append(fname)
                    if idx == 0:
                        with open(fname, "rb") as f:
                            concat_dataset_fingerprints = json.load(f)
                        if (
                            "foreground_intensity_properties_per_channel"
                            in concat_dataset_fingerprints
                            and concat_dataset_fingerprints[
                                "foreground_intensity_properties_per_channel"
                            ]
                        ):
                            # local_intensityproperties = collections.OrderedDict()
                            for mod_id, _ in concat_dataset_fingerprints[
                                "foreground_intensity_properties_per_channel"
                            ].items():
                                voxels_in_foreground[
                                    mod_id
                                ] = concat_dataset_fingerprints[
                                    "foreground_intensity_properties_per_channel"
                                ][
                                    mod_id
                                ][
                                    "v"
                                ]
                                # local_intensityproperties[
                                #     mod_id
                                # ] = collections.OrderedDict()
                                # local_intensityproperties[mod_id][
                                #     "local_props"
                                # ] = concat_dataset_fingerprints["foreground_intensity_properties_per_channel"][
                                #     mod_id
                                # ][
                                #     "local_props"
                                # ]
                                print(
                                    f"Processed fingerprint {idx} of modality {mod_id}!"
                                )
                            # concat_dataset_fingerprints[
                            #     "foreground_intensity_properties_per_channel"
                            # ] = local_intensityproperties
                    else:
                        with open(fname, "rb") as f:
                            dataset_fingerprints = json.load(f)
                        for k in [
                            "shapes_after_crop",
                            "spacings",
                        ]:  # ["all_sizes", "all_spacings"]:
                            concat_dataset_fingerprints[k] = (
                                concat_dataset_fingerprints[k] + dataset_fingerprints[k]
                            )
                        # concat_dataset_fingerprints["size_reductions"].update(
                        #     dataset_fingerprints["size_reductions"]
                        # )
                        if (
                            "foreground_intensity_properties_per_channel"
                            in concat_dataset_fingerprints
                            and concat_dataset_fingerprints[
                                "foreground_intensity_properties_per_channel"
                            ]
                        ):
                            for (
                                mod_id,
                                intensityproperties,
                            ) in concat_dataset_fingerprints[
                                "foreground_intensity_properties_per_channel"
                            ].items():
                                voxels_in_foreground[mod_id] = (
                                    voxels_in_foreground[mod_id]
                                    + dataset_fingerprints[
                                        "foreground_intensity_properties_per_channel"
                                    ][mod_id]["v"]
                                )
                                # concat_dataset_fingerprints["foreground_intensity_properties_per_channel"][
                                #     mod_id
                                # ]["local_props"].update(
                                #     dataset_fingerprints["foreground_intensity_properties_per_channel"][mod_id][
                                #         "local_props"
                                #     ]
                                # )
                                print(
                                    f"Processed fingerprint {idx} of modality {mod_id}."
                                )

            datasets = []
            for idx, fname in enumerate(preprocessing_path.rglob("dataset.json")):
                with open(fname, "rb") as f:
                    datasets.append(json.load(f))

            if len(datasets) > 0:
                for i, dataset in enumerate(datasets):
                    if i == 0:
                        ref_channels = dataset["channel_names"]
                        ref_labels = dataset["labels"]
                    else:
                        current_channels = dataset["channel_names"]
                        current_labels = dataset["labels"]
                        assert ref_channels == current_channels
                        assert ref_labels == current_labels

            #     if "nnUNet_preprocessed" in str(fname):
            #         dataset_files.append(fname)
            #         if idx == 0:
            #             with open(fname, "rb") as f:
            #                 concat_dataset = json.load(f)
            #             for k in ["labels", "channel_names"]:
            #                 if k in concet_dataset and concat_dataset[k]:

            # for k in ["all_classes", "modalities"]:
            #     assert json.dumps(dataset_fingerprints[k]) == json.dumps(
            #                     concat_dataset_fingerprints[k]
            #                 )
            #         # print(fname)
            print(
                f"Number of to be aggregated data fingerprints: {len(dataset_fingerprints_files)}."
            )
            if (
                "foreground_intensity_properties_per_channel"
                in concat_dataset_fingerprints
                and concat_dataset_fingerprints[
                    "foreground_intensity_properties_per_channel"
                ]
            ):
                global_intensityproperties = (
                    nnUNetFederatedTraining.collect_intensity_properties(
                        voxels_in_foreground
                    )
                )
                for mod_id, _ in concat_dataset_fingerprints[
                    "foreground_intensity_properties_per_channel"
                ].items():
                    print(
                        f"Number of aggregated data fingerprints {idx} of modality {mod_id}."
                    )
                    concat_dataset_fingerprints[
                        "foreground_intensity_properties_per_channel"
                    ][str(mod_id)].update(global_intensityproperties[int(mod_id)])

            for fname in dataset_fingerprints_files:
                with open(fname, "w") as f:
                    json.dump(concat_dataset_fingerprints, f)

            # Dummy creation of nnunet-training folder, because a tar is expected in the next round due
            # to from_previous_dag_run not None. Mybe there is a better solution for the future...
            for instance_name, tmp_site_info in tmp_central_site_info.items():
                nnunet_training_file_path = tmp_site_info["file_paths"][0].replace(
                    "nnunet-preprocess", "nnunet-training"
                )
                nnunet_training_dir = nnunet_training_file_path.replace(".tar", "")
                Path(nnunet_training_dir).mkdir(exist_ok=True)
                tmp_site_info["file_paths"].append(nnunet_training_file_path)
                nnunet_training_next_object_name = tmp_site_info["next_object_names"][
                    0
                ].replace("nnunet-preprocess", "nnunet-training")
                tmp_site_info["next_object_names"].append(
                    nnunet_training_next_object_name
                )
        else:
            print("Training mode")
            if federated_round >= 0:
                self.tensorboard_logs(federated_round)
            current_federated_round_dir = Path(
                os.path.join(self.fl_working_dir, str(federated_round))
            )
            print(psutil.Process(os.getpid()).memory_info().rss / 1024**2)

            # Not 100% sure if it is necessary to put those into functions, I did this to be sure to not allocated unnecssary memory...
            def _sum_state_dicts(fname, idx):
                checkpoint = torch.load(fname, map_location=torch.device("cpu"))
                if idx == 0:
                    sum_state_dict = checkpoint["state_dict"]
                else:
                    sum_state_dict = torch.load("tmp_state_dict.pt")
                    for key, value in checkpoint["state_dict"].items():
                        sum_state_dict[key] = (
                            sum_state_dict[key] + checkpoint["state_dict"][key]
                        )
                torch.save(sum_state_dict, "tmp_state_dict.pt")

            def _save_state_dict(fname, averaged_state_dict):
                checkpoint = torch.load(fname, map_location=torch.device("cpu"))
                checkpoint["state_dict"] = averaged_state_dict
                torch.save(checkpoint, fname)

            print("Loading averaged checkpoints")
            for idx, fname in enumerate(
                current_federated_round_dir.rglob("model_final_checkpoint.model")
            ):
                print(fname)
                _sum_state_dicts(fname, idx)
                print(psutil.Process(os.getpid()).memory_info().rss / 1024**2)

            sum_state_dict = torch.load("tmp_state_dict.pt")
            os.remove("tmp_state_dict.pt")

            averaged_state_dict = collections.OrderedDict()
            for key, value in sum_state_dict.items():
                averaged_state_dict[key] = sum_state_dict[key] / (idx + 1.0)

            print("Saving averaged checkpoints")
            for idx, fname in enumerate(
                current_federated_round_dir.rglob("model_final_checkpoint.model")
            ):
                print(fname)
                _save_state_dict(fname, averaged_state_dict)
                print(psutil.Process(os.getpid()).memory_info().rss / 1024**2)

            if (
                self.remote_conf_data["federated_form"]["federated_total_rounds"]
                == federated_round + 1
            ):
                src = (
                    current_federated_round_dir
                    / self.remote_sites[0]["instance_name"]
                    / "nnunet-training"
                )
                dst = os.path.join("/", self.workflow_dir, "nnunet-training")
                print(
                    f"Last round! Copying final nnunet-training files from {src} to {dst}"
                )
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src=src, dst=dst)
                shutil.copyfile(
                    src=os.path.join(os.path.dirname(fname), "dataset.json"),
                    dst=os.path.join(dst, "dataset.json"),
                )  # A little bit ugly... but necessary for Bin2Dcm operator

    @timeit
    def on_wait_for_jobs_end(self, federated_round):
        if federated_round == -2:
            print("Taking actions...")
            self.remote_conf_data["federated_form"]["skip_operators"].remove(
                "nnunet-training"
            )
            self.remote_conf_data["federated_form"][
                "skip_operators"
            ] = self.remote_conf_data["federated_form"]["skip_operators"] + [
                "get-input-data",
                "get-ref-series-ct",
                "dcmseg2nrrd",
                "dcm-converter-ct",
                "seg-check",
            ]
            self.remote_conf_data["workflow_form"][
                "prep_increment_step"
            ] = "from_dataset_properties"
        elif federated_round == -1:
            print("Removing nnunet-preprocess from federated_operators")
            self.remote_conf_data["federated_form"]["federated_operators"].remove(
                "nnunet-preprocess"
            )
            print("Setting prep_increment_step to empty")
            self.remote_conf_data["workflow_form"]["prep_increment_step"] = ""
        else:
            self.remote_conf_data["workflow_form"]["train_continue"] = True
            self.run_in_parallel = True
        print(
            f"Current fl_round={federated_round} out of {self.remote_conf_data['federated_form']['federated_total_rounds']} total fl_rounds."
        )


if __name__ == "__main__":
    kaapana_ft = nnUNetFederatedTraining()
    if (
        "federated_round" in kaapana_ft.remote_conf_data["federated_form"]
        and kaapana_ft.remote_conf_data["federated_form"]["federated_round"] >= 0
    ):
        print("Skipping preprocessing since we are running in recovery mode!")
    else:
        kaapana_ft.train_step(-2)
        kaapana_ft.train_step(-1)
    kaapana_ft.train()
    kaapana_ft.clean_up_minio()
