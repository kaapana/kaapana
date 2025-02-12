import collections
import json
import logging
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path

import torch
from kaapana_federated.JobScheduling import RemoteJobScheduler
from kaapana_federated.KaapanaFedServices import (
    KaapanaFedDataService,
    KaapanaFedWorkflowService,
)
from kaapanapy.settings import OperatorSettings


class FederatedExecutionConfig:
    @property
    def instance_names(self):
        return self.remote_conf_data.get("instance_names", [])

    def update_federated_round(self, new_federated_round: int):
        self.remote_conf_data["federated_form"]["federated_round"] = new_federated_round

    @property
    def bucket(self) -> str:
        return self.remote_conf_data["federated_form"]["federated_bucket"]

    @property
    def username(self) -> str:
        return self.local_conf_data["workflow_form"]["username"]

    @property
    def workflow_id(self) -> str:
        return self.local_conf_data["workflow_form"]["workflow_id"]

    @property
    def remote_conf_federated_form(self) -> dict:
        return self.remote_conf_data["federated_form"]

    @property
    def federated_dir(self) -> Path:
        return Path(self.remote_conf_data["federated_form"]["federated_dir"])

    def __init__(self, conf_file: Path):
        self.remote_conf_data = {}
        self.local_conf_data = {}
        self.tmp_federated_site_info = {}
        self.federated_dir = operator_settings.run_id
        self.load_config()

    def create_recovery_conf(self, federated_round: int):
        print("Recovery conf for round {}")
        self.tmp_federated_site_info = {
            instance_name: {
                k: tmp_site_info[k]
                for k in ["from_previous_dag_run", "before_previous_dag_run"]
            }
            for instance_name, tmp_site_info in self.tmp_federated_site_info.items()
        }
        recovery_conf = {
            "remote": False,
            "dag_id": os.getenv("DAG_ID"),
            "instance_names": [
                instance_name
                for instance_name, _ in self.tmp_federated_site_info.items()
            ],
            "form_data": {
                **self.local_conf_data,
                **{f"external_schema_{k}": v for k, v in self.remote_conf_data.items()},
                "tmp_federated_site_info": self.tmp_federated_site_info,
            },
        }
        print("Recovery conf formatted")
        print(json.dumps(recovery_conf, indent=2))
        print("Recovery conf in one line")
        print(json.dumps(recovery_conf))
        recovery_path = os.path.join(
            self.operator_out_dir, str(federated_round), "recovery_conf.json"
        )
        # os.makedirs(os.path.basename(recovery_path), exist_ok=True)
        os.makedirs(os.path.dirname(recovery_path), exist_ok=True)
        with open(recovery_path, "w", encoding="utf-8") as jsonData:
            json.dump(
                recovery_conf, jsonData, indent=2, sort_keys=True, ensure_ascii=True
            )

        minio_recovery_path = os.path.join(
            self.federated_dir, str(federated_round), "recovery_conf.json"
        )
        print(
            f"Uploading recovery_conf to MinIO: {self.remote_conf_data['federated_form']['federated_bucket']}/{minio_recovery_path}"
        )
        self.minioClient.fput_object(
            self.remote_conf_data["federated_form"]["federated_bucket"],  # minio bucket
            minio_recovery_path,  # path in minio bucket
            recovery_path,  # path of file in current workflow dir
        )

    def load_config(self, config_file=None):
        with open(config_file) as f:
            conf_data = json.load(f)

        # Init external_schema_federated_form
        if "external_schema_federated_form" not in conf_data:
            conf_data["external_schema_federated_form"] = {}

        if "federated_bucket" not in conf_data["external_schema_federated_form"]:
            conf_data["external_schema_federated_form"]["federated_bucket"] = conf_data[
                "external_schema_federated_form"
            ]["remote_dag_id"]

        if "federated_dir" not in conf_data["external_schema_federated_form"]:
            conf_data["external_schema_federated_form"][
                "federated_dir"
            ] = self.federated_dir

        for k, v in conf_data.items():
            if k.startswith("external_schema_"):
                self.remote_conf_data[k.replace("external_schema_", "")] = v
            elif k == "tmp_federated_site_info":
                self.tmp_federated_site_info = v
            elif k in ["client_job_id", "x_auth_token"]:
                pass
            elif k == "project_form":
                self.remote_conf_data["project_form"] = v
            else:
                self.local_conf_data[k] = v

        # FL aggregation strategy
        if "aggregation_strategy" in self.remote_conf_data["federated_form"]:
            # get defined FL aggregation strategy
            self.aggregation_strategy = self.remote_conf_data["federated_form"][
                "aggregation_strategy"
            ]["agg_strategy_method"]
            # special params for FedDC
            if self.aggregation_strategy == "feddc":
                self.agg_rate = self.remote_conf_data["federated_form"][
                    "aggregation_strategy"
                ]["feddc_aggregation_rate"]
                self.dc_rate = self.remote_conf_data["federated_form"][
                    "aggregation_strategy"
                ]["feddc_daisychaining_rate"]

        federated_form = self.remote_conf_data.get(federated_form, {})
        if "federated_round" in federated_form:
            self.federated_round_start = federated_form["federated_round"] + 1
            self.log.info(
                "Running in recovery mode and starting from round %d",
                self.federated_round_start,
            )
        else:
            self.federated_round_start = 0


class KaapanaFedOrchestratorBase(ABC):
    def __init__(self):
        self.log = logging.getLogger(__name__)
        operator_settings = OperatorSettings()

        self.conf = FederatedExecutionConfig(
            Path(operator_settings.workflow_dir) / "conf" / "conf.json"
        )
        self.data_service = KaapanaFedDataService(
            bucket=self.conf.bucket,
            federated_dir=self.conf.federated_dir,
            operator_out_dir=Path(self.operator_settings.workflow_dir)
            / self.operator_settings.operator_out_dir,
        )
        self.remote_instances = RemoteJobScheduler(
            self.conf.instance_names, KaapanaFedWorkflowService()
        )

    def distribute_jobs(self, federated_round: int):
        for instance_name in self.remote_instances.instance_names:
            self.conf["federated_round"] = federated_round

            # update previous_dag_run attributes necessary for caching and restarting processes
            self.conf["from_previous_dag_run"] = self.remote_instances.get_jobs(
                instance_name=instance_name, history_index=0
            ).run_id
            self.conf["before_previous_dag_run"] = self.remote_instances.get_jobs(
                instance_name=instance_name, history_index=1
            ).run_id

            self.remote_instances.create_job(
                instance_name=instance_name,
                dag_id=self.conf["remote_dag_id"],
                conf_data=self.remote_conf_data,
                username=self.conf.username,
                workflow_id=self.conf.workflow_id,
            )

    def wait_for_jobs(self):
        self.remote_instances.wait_for_jobs()

    def download_data(self, federated_round: int):
        for instance in self.remote_instances.instances.values():
            file2serverObj = self.data_service.download(
                federated_round=federated_round,
                instance_name=instance.instance_name,
                secret=instance.fernet_key,
            )

            current_federated_round_dir = self.data_service.federated_round_dir(
                federated_round=federated_round
            )
            next_federated_round_dir = self.data_service.federated_round_dir(
                federated_round=federated_round + 1
            )
            file_paths = [str(file) for file in file2serverObj.items()]
            object_paths = [file2serverObj[file_path] for file_path in file_paths]
            next_object_names = [
                obj.replace(current_federated_round_dir, next_federated_round_dir)
                for obj in object_paths
            ]
            tmp_site_info["file_paths"] = file_paths
            tmp_site_info["next_object_names"] = next_object_names

            self.data_service.clean_up_round(
                federated_round=federated_round - 1,
                instance_name=instance.instance_name,
            )

    def upload_data(self, federated_round: int):
        for instance in self.remote_instances.values():
            for file_path, next_object_name in zip(
                tmp_site_info["file_paths"], tmp_site_info["next_object_names"]
            ):
                self.data_service.upload_package(
                    local_path=file_path,
                    server_target_path=next_object_name,
                    secret=instance.fernet_key,
                )

    def _cleanup_working_dir(self, federated_round: int):
        directory = self.operator_out_dir / str(federated_round)
        if directory.is_dir():
            shutil.rmtree(directory)


class KaapanaFederatedTrainingBase(KaapanaFedOrchestratorBase):
    def __init__(
        self,
        workflow_dir=None,
        access_key="kaapanaminio",
        secret_key="Kaapana2020",
        minio_host=None,
        minio_port="9000",
    ):
        super().__init__(workflow_dir, access_key, secret_key, minio_host, minio_port)
        self.run_in_parallel = False

    @abstractmethod
    # @timeit
    def update_data(self, federated_round, tmp_central_site_info):
        pass

    # @timeit
    def load_model_weights(self, current_federated_round_dir=None):
        """
        Load checkpoints and return as dict.
        """
        print("Load checkpoints and return as dict.")
        site_model_weights_dict = collections.OrderedDict()
        for idx, fname in enumerate(
            current_federated_round_dir.rglob("checkpoint_final.pth")
        ):
            print(f"Loading model_weights from: {fname}")
            checkpoint = torch.load(fname, map_location=torch.device("cpu"))

            # retrieve site_name from current_federated_round_dir
            modified_fname = str(fname).replace(str(current_federated_round_dir), "")
            site_name = modified_fname.split("/")[1]

            site_model_weights_dict[site_name] = checkpoint["network_weights"]
        return site_model_weights_dict

    # @timeit
    def _save_model_weights(self, fname=None, model_weights=None):
        """
        Saves model_weights to checkpoint in fname.
        """
        checkpoint = torch.load(str(fname), map_location=torch.device("cpu"))
        # delete here fname first and save it then again from scratch
        os.remove(fname)
        checkpoint["network_weights"] = model_weights
        torch.save(checkpoint, str(fname))

    # @timeit
    def save_model_weights(
        self, current_federated_round_dir=None, processed_site_model_weights_dict=None
    ):
        """
        Save processed model to site-corresponding minio folders.
        """
        print("Saving processed model checkpoints")
        for idx, fname in enumerate(
            current_federated_round_dir.rglob("checkpoint_final.pth")
        ):
            # retrieve site_name from current_federated_round_dir
            modified_fname = str(fname).replace(str(current_federated_round_dir), "")
            site_name = modified_fname.split("/")[1]

            print(f"Save centrally processed model to {site_name}")

            self._save_model_weights(
                str(fname), processed_site_model_weights_dict[site_name]
            )

        return str(fname)

    # @timeit
    def on_wait_for_jobs_end(self, federated_round):
        pass

    # @timeit
    def central_steps(self, federated_round: int, tmp_central_site_info):
        # Working with downloaded objects
        self.download_data(
            federated_round=federated_round, tmp_central_site_info=tmp_central_site_info
        )
        self.update_data(
            federated_round=federated_round, tmp_central_site_info=tmp_central_site_info
        )
        self.upload_data(
            federated_round=federated_round, tmp_central_site_info=tmp_central_site_info
        )

    # @timeit
    def train_step(self, federated_round: int):
        if not self.run_in_parallel:
            self.distribute_jobs(federated_round=federated_round)

        self.wait_for_jobs(federated_round=federated_round)

        tmp_central_site_info = {
            instance_name: tmp_site_info
            for instance_name, tmp_site_info in self.tmp_federated_site_info.items()
        }

        self.on_wait_for_jobs_end(federated_round=federated_round)
        self.create_recovery_conf(federated_round=federated_round)

        federated_total_rounds = self.remote_conf_data["federated_form"][
            "federated_total_rounds"
        ]
        if self.run_in_parallel and (federated_round + 1) < federated_total_rounds:
            self.distribute_jobs(federated_round=federated_round + 1)

        self.central_steps(
            federated_round=federated_round, tmp_central_site_info=tmp_central_site_info
        )

        if federated_round > 0:
            previous_round = federated_round - 1
            self.log(
                "Remove files from previous fl round %d (current round %d)",
                previous_round,
                federated_round,
            )
            self._cleanup_working_dir(previous_round)

    # @timeit
    def train(self):
        federated_total_rounds = self.remote_conf_data["federated_form"][
            "federated_total_rounds"
        ]
        for federated_round in range(
            self.federated_round_start, federated_total_rounds
        ):
            self.log.info(
                "Beginning Federated Round %d (total: %d)",
                federated_round,
                federated_total_rounds,
            )
            self.train_step(federated_round=federated_round)
