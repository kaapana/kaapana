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
import psutil
import numpy as np
import math

sys.path.insert(0, "/")
sys.path.insert(0, "/kaapana/app")
from kaapana_federated.KaapanaFederatedTraining import (
    KaapanaFederatedTrainingBase,
    timeit,
)


class nnUNetFederatedTraining(KaapanaFederatedTrainingBase):
    @staticmethod
    def collect_intensity_properties(v_per_mod, num_processes=8):
        """
        Method computes from voxel intensities per client and modality, the global intensity statistics/properties per modality.

        Input:
        * v_per_mod: List of voxel values per client and per modality
        * num_processes

        Output:
        * results: Global intensity properties per modality (global over all clients).
        """
        num_modalities = len(v_per_mod)
        p = Pool(num_processes)

        results = OrderedDict()
        for mod_id in range(num_modalities):
            results[mod_id] = OrderedDict()
            w = []
            for iv in v_per_mod[str(mod_id)]:
                w += iv

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

    def estimate_global_intensity_properties(self, intensities_per_mod):
        """
        Method estimates from intensities properties per client and modality,
        the global intensity statistics/properties per modality.

        Input:
        * intensities_per_mod: List of intensities properties per client and per modality

        Output:
        * results: Global intensity properties per modality (global over all clients).
        """
        results = {}

        # Iterate over modalities
        for mod_id, all_intensities in intensities_per_mod.items():
            # Initialize accumulators
            total_mean = 0.0
            total_variance = 0.0
            total_median = 0.0
            total_percentile_00_5 = 0.0
            total_percentile_99_5 = 0.0
            total_samples = 0
            glob_min = float("inf")
            glob_max = float("-inf")

            for stats in all_intensities:
                mean = stats["mean"]
                std = stats["std"]
                median = stats["median"]
                percentile_00_5 = stats["percentile_00_5"]
                percentile_99_5 = stats["percentile_99_5"]
                n = stats["n"]

                # Update global mean
                total_mean += mean * n
                total_samples += n

                # Update global standard deviation
                total_variance += n * (
                    std**2 + (mean - (total_mean / total_samples)) ** 2
                )

                # Update global min and max
                glob_min = min(glob_min, stats["min"])
                glob_max = max(glob_max, stats["max"])

                # Update global median and percentiles
                total_median += median * n
                total_percentile_00_5 += percentile_00_5 * n
                total_percentile_99_5 += percentile_99_5 * n

            # Final global mean and standard deviation
            glob_mean = total_mean / total_samples
            glob_std = math.sqrt(total_variance / total_samples)

            # Estimate global median and percentiles via weighted mean of client's medians and percentiles
            # glob_median = np.mean([x["median"] for x in all_intensities])
            # glob_percentile_00_5 = np.mean([x["percentile_00_5"] for x in all_intensities])
            # glob_percentile_99_5 = np.mean([x["percentile_99_5"] for x in all_intensities])
            glob_median = total_median / total_samples
            glob_percentile_00_5 = total_percentile_00_5 / total_samples
            glob_percentile_99_5 = total_percentile_99_5 / total_samples

            # Store results in the dictionary
            results[int(mod_id)] = {
                "mn": glob_min,
                "mx": glob_max,
                "mean": glob_mean,
                "sd": glob_std,
                "median": glob_median,
                "percentile_00_5": glob_percentile_00_5,
                "percentile_99_5": glob_percentile_99_5,
            }

        return results

    def __init__(self, workflow_dir=None):
        super().__init__(workflow_dir=workflow_dir)

        # recovery mode
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

        # setting epochs configs to be also available in client's nnunet-training workflows
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

        # set to 'to_dataset_properties' to start training with generation of dataset_properties at clients
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

        # make federated data fingerprint strategy available in client's nnunet-training workflow
        self.remote_conf_data["workflow_form"][
            "fed_global_fingerprint"
        ] = self.remote_conf_data["federated_form"]["global_fingerprint"]
        # make number of FL clients availiable in client's nnunet-training workflow
        self.remote_conf_data["workflow_form"]["fed_num_clients"] = len(
            self.remote_conf_data["instance_names"]
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

            # iterate over client's fingerprints and concatenate them
            voxels_in_foreground = {}
            clients_intensity_properties = {}
            dataset_fingerprints_files = []
            for idx, fname in enumerate(
                preprocessing_path.rglob("dataset_fingerprint.json")
            ):
                if "nnUNet_preprocessed" in str(fname):
                    dataset_fingerprints_files.append(fname)

                    # process fingerprint of first client
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
                            # iterate over modalities
                            for mod_id, _ in concat_dataset_fingerprints[
                                "foreground_intensity_properties_per_channel"
                            ].items():
                                if (
                                    self.remote_conf_data["workflow_form"][
                                        "fed_global_fingerprint"
                                    ]
                                    == "accurate"
                                ):
                                    voxels_in_foreground[
                                        mod_id
                                    ] = concat_dataset_fingerprints[
                                        "foreground_intensity_properties_per_channel"
                                    ][
                                        mod_id
                                    ][
                                        "v"
                                    ]
                                elif (
                                    self.remote_conf_data["workflow_form"][
                                        "fed_global_fingerprint"
                                    ]
                                    == "estimate"
                                ):
                                    clients_intensity_properties[mod_id] = [
                                        {
                                            **concat_dataset_fingerprints[
                                                "foreground_intensity_properties_per_channel"
                                            ][mod_id],
                                            "n": len(
                                                concat_dataset_fingerprints["spacings"]
                                            ),
                                        }
                                    ]

                                print(
                                    f"Processed first fingerprint {idx} of modality {mod_id}!"
                                )
                    # process fingerprints of other clients
                    else:
                        with open(fname, "rb") as f:
                            dataset_fingerprints = json.load(f)

                        # concatenate 'shapes' and 'spacings'
                        for k in [
                            "shapes_after_crop",
                            "spacings",
                        ]:
                            concat_dataset_fingerprints[k] = (
                                concat_dataset_fingerprints[k] + dataset_fingerprints[k]
                            )

                        # concatenate data fingerprint intensities or sampled voxels
                        if (
                            "foreground_intensity_properties_per_channel"
                            in concat_dataset_fingerprints
                            and concat_dataset_fingerprints[
                                "foreground_intensity_properties_per_channel"
                            ]
                        ):
                            # iterate over modalities
                            for (
                                mod_id,
                                intensityproperties,
                            ) in concat_dataset_fingerprints[
                                "foreground_intensity_properties_per_channel"
                            ].items():
                                if (
                                    self.remote_conf_data["workflow_form"][
                                        "fed_global_fingerprint"
                                    ]
                                    == "accurate"
                                ):
                                    voxels_in_foreground[mod_id] = (
                                        voxels_in_foreground[mod_id]
                                        + dataset_fingerprints[
                                            "foreground_intensity_properties_per_channel"
                                        ][mod_id]["v"]
                                    )
                                if (
                                    self.remote_conf_data["workflow_form"][
                                        "fed_global_fingerprint"
                                    ]
                                    == "estimate"
                                ):
                                    clients_intensity_properties[mod_id].append(
                                        {
                                            **concat_dataset_fingerprints[
                                                "foreground_intensity_properties_per_channel"
                                            ][mod_id],
                                            "n": len(dataset_fingerprints["spacings"]),
                                        }
                                    )
                                print(
                                    f"Concatenated fingerprint {idx} of modality {mod_id}."
                                )

            datasets = []
            for idx, fname in enumerate(preprocessing_path.rglob("dataset.json")):
                with open(fname, "rb") as f:
                    datasets.append(json.load(f))

            # check channel_names/modality and label consistency among FL clients
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

            print(
                f"Number of to be aggregated data fingerprints: {len(dataset_fingerprints_files)}."
            )
            # aggregate extracted and concatenated data fingerprints to obtain global data fingerprint
            if (
                "foreground_intensity_properties_per_channel"
                in concat_dataset_fingerprints
                and concat_dataset_fingerprints[
                    "foreground_intensity_properties_per_channel"
                ]
            ):
                # compute or estimate global intensity properties based
                if (
                    self.remote_conf_data["workflow_form"]["fed_global_fingerprint"]
                    == "accurate"
                ):
                    print(
                        "Accurate, slower and less privacy-preserving computation of global dataset fingerprint!"
                    )
                    global_intensityproperties = (
                        nnUNetFederatedTraining.collect_intensity_properties(
                            voxels_in_foreground
                        )
                    )
                elif (
                    self.remote_conf_data["workflow_form"]["fed_global_fingerprint"]
                    == "estimate"
                ):
                    print(
                        "Estimated, faster and more privacy-preserving computation of global dataset fingerprint!"
                    )
                    global_intensityproperties = (
                        self.estimate_global_intensity_properties(
                            clients_intensity_properties
                        )
                    )

                # write obtained global_intensity properties to result
                for mod_id, _ in concat_dataset_fingerprints[
                    "foreground_intensity_properties_per_channel"
                ].items():
                    print(
                        f"Number of aggregated data fingerprints {idx} of modality {mod_id}."
                    )
                    concat_dataset_fingerprints[
                        "foreground_intensity_properties_per_channel"
                    ][str(mod_id)].update(global_intensityproperties[int(mod_id)])
                    print(0)

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

            ### FL Aggregation during training ###
            # load model_weights
            site_model_weights_dict = self.load_model_weights(
                current_federated_round_dir
            )
            # process model_weights according to aggregation method
            if self.aggregation_strategy == "fedavg":
                # FedAvg
                processed_site_model_weights_dict = self.fed_avg(
                    site_model_weights_dict
                )
            elif self.aggregation_strategy == "feddc":
                if federated_round == -1:
                    # average in fl_round=-1 to initialize everywhere w/ same model
                    processed_site_model_weights_dict = self.fed_avg(
                        site_model_weights_dict
                    )
                else:
                    # FedDC
                    processed_site_model_weights_dict = self.fed_dc(
                        site_model_weights_dict, federated_round
                    )
            else:
                raise ValueError(
                    "No Federated Learning method is given. Choose between 'fedavg', 'feddc'."
                )
            # save model_weights to server's minio
            fname = self.save_model_weights(
                current_federated_round_dir, processed_site_model_weights_dict
            )

            # last fl_round
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
                "mask2nifti",
                "filter-masks",
                "fuse-masks",
                "rename-seg-label-names",
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
            # set run_in_parallel to False if model communication is too slow or models are too large
            self.run_in_parallel = False
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
