from cryptography.fernet import Fernet
import requests
import time
import numpy as np
import json
import os
import uuid
import shutil
import collections
import torch
import random
import tarfile
import functools
from minio import Minio
from abc import ABC, abstractmethod
from requests.adapters import HTTPAdapter
from abc import ABC, abstractmethod
from kaapanapy.helper.HelperMinioSessionManager import HelperMinioSessionManager
from minio.deleteobjects import DeleteObject
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

SERVICES_NAMESPACE = os.getenv("SERVICES_NAMESPACE", None)
assert SERVICES_NAMESPACE != None


# Todo move in Jonas library as normal function
def timeit(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        ts = time.time()
        x = func(self, *args, **kwargs)
        te = time.time()
        self.json_writer.append_data_dict(
            {
                "name": func.__name__,
                "execution_time": te - ts,
                "timestamp": time.time(),
                "args": args,
                "kwargs": kwargs,
            }
        )
        return x

    return wrapper


# Todo move in Jonas library as normal function
class JsonWriter(object):
    @staticmethod
    def _write_json(filename, data):
        with open(filename, "w") as json_file:
            json.dump(data, json_file)

    @staticmethod
    def _load_json(filename):
        try:
            with open(filename) as json_file:
                workflow_data = json.load(json_file)
        except FileNotFoundError:
            workflow_data = []
        return workflow_data

    def __init__(self, log_dir) -> None:
        self.filename = os.path.join(log_dir, "fl_stats.json")
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        # not accumulating anything because this leads to a decrease in speed over many epochs!

    def append_data_dict(self, data_dict):
        workflow_data = JsonWriter._load_json(self.filename)
        workflow_data.append(data_dict)
        JsonWriter._write_json(self.filename, workflow_data)


# Todo move in Jonas library as normal function
def requests_retry_session(
    retries=16,
    backoff_factor=1,
    status_forcelist=[404, 429, 500, 502, 503, 504],
    session=None,
    use_proxies=False,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    if use_proxies is True:
        proxies = {
            "http": os.getenv("PROXY", None),
            "https": os.getenv("PROXY", None),
            "no_proxy": ".svc,.svc.cluster,.svc.cluster.local",
        }
        session.proxies.update(proxies)

    return session


def minio_rmtree(minioClient, bucket_name, object_name):
    delete_object_list = map(
        lambda x: DeleteObject(x.object_name),
        minioClient.list_objects(bucket_name, object_name, recursive=True),
    )
    errors = minioClient.remove_objects(bucket_name, delete_object_list)
    for error in errors:
        raise NameError("Error occured when deleting object", error)


class KaapanaFederatedTrainingBase(ABC):
    # Todo move in Jonas library as normal function
    @staticmethod
    def fernet_encryptfile(filepath, key):
        if key == "deactivated":
            return
        fernet = Fernet(key.encode())
        with open(filepath, "rb") as file:
            original = file.read()
        encrypted = fernet.encrypt(original)
        with open(filepath, "wb") as encrypted_file:
            encrypted_file.write(encrypted)

    # Todo move in Jonas library as normal function
    @staticmethod
    def fernet_decryptfile(filepath, key):
        if key == "deactivated":
            return
        fernet = Fernet(key.encode())
        with open(filepath, "rb") as enc_file:
            encrypted = enc_file.read()
        decrypted = fernet.decrypt(encrypted)
        with open(filepath, "wb") as dec_file:
            dec_file.write(decrypted)

    # Todo move in Jonas library as normal function
    def apply_untar_action(src_filename, dst_dir):
        print(f"Untar {src_filename} to {dst_dir}")
        with tarfile.open(
            src_filename, "r:gz" if src_filename.endswith("gz") is True else "r"
        ) as tar:
            tar.extractall(dst_dir)

    # Todo move in Jonas library as normal function
    def apply_tar_action(dst_filename, src_dir):
        print(f"Tar {src_dir} to {dst_filename}")
        with tarfile.open(
            dst_filename, "w:gz" if dst_filename.endswith("gz") is True else "w"
        ) as tar:
            tar.add(src_dir, arcname=os.path.basename(src_dir))

    # Todo move in Jonas library as normal function
    @staticmethod
    def raise_kaapana_connection_error(r):
        if r.history:
            raise ConnectionError(
                "You were redirect to the auth page. Your token is not valid!"
            )
        try:
            r.raise_for_status()
        except:
            raise ValueError(
                f"Something was not okay with your request code {r}: {r.text}!"
            )

    def get_conf(self, workflow_dir=None):
        with open(os.path.join("/", workflow_dir, "conf", "conf.json"), "r") as f:
            conf_data = json.load(f)
        if "external_schema_federated_form" not in conf_data:
            conf_data["external_schema_federated_form"] = {}
        # Get federated_folder, defaulting to remote_dag_id if not present, and remove it from conf_data
        federated_folder = conf_data["external_schema_federated_form"].pop(
            "federated_folder",
            conf_data["external_schema_federated_form"]["remote_dag_id"],
        )

        federated_dir = conf_data["external_schema_federated_form"].get(
            "federated_dir", self.federated_dir
        )
        # Store the combined path back in federated_dir
        conf_data["external_schema_federated_form"]["federated_dir"] = os.path.join(
            federated_folder, federated_dir
        )

        return conf_data

    def __init__(
        self,
        workflow_dir=None,
    ):
        self.run_in_parallel = False
        self.federated_dir = os.getenv("RUN_ID", str(uuid.uuid4()))
        self.workflow_dir = workflow_dir or os.getenv("WORKFLOW_DIR")
        print("working directory", self.workflow_dir)

        conf_data = self.get_conf(self.workflow_dir)
        print(conf_data)

        self.remote_conf_data = {}
        self.local_conf_data = {}
        self.tmp_federated_site_info = {}
        print("Splitting conf data")
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

        self.fl_working_dir = os.path.join(
            "/",
            self.workflow_dir,
            os.getenv("OPERATOR_OUT_DIR", "federated-operator"),
        )
        print(self.fl_working_dir)

        self.json_writer = JsonWriter(log_dir=self.fl_working_dir)

        self.client_url = (
            f"http://kaapana-backend-service.{SERVICES_NAMESPACE}.svc:5000/client"
        )
        with requests.Session() as s:
            r = requests_retry_session(session=s).get(
                f"{self.client_url}/kaapana-instance"
            )
        KaapanaFederatedTrainingBase.raise_kaapana_connection_error(r)
        self.client_network = r.json()

        if "instance_names" in self.remote_conf_data:
            instance_names = self.remote_conf_data["instance_names"]
        else:
            instance_names = []

        if (
            "federated_form" in self.remote_conf_data
            and "federated_round" in self.remote_conf_data["federated_form"]
        ):
            self.federated_round_start = (
                self.remote_conf_data["federated_form"]["federated_round"] + 1
            )
            print(
                f"Running in recovery mode and starting from round {self.federated_round_start}"
            )
        else:
            self.federated_round_start = 0
        print(instance_names)
        with requests.Session() as s:
            r = requests_retry_session(session=s).post(
                f"{self.client_url}/get-kaapana-instances",
                json={"instance_names": instance_names},
            )
        KaapanaFederatedTrainingBase.raise_kaapana_connection_error(r)
        self.remote_sites = r.json()

        # instantiate Minio client
        self.minioSession: Minio = HelperMinioSessionManager()

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

    @timeit
    def distribute_jobs(self, federated_round):
        # Starting round!
        self.remote_conf_data["federated_form"]["federated_round"] = federated_round

        for site_info in self.remote_sites:
            # update previous_dag_run attributes necessary for caching and restarting processes
            if site_info["instance_name"] not in self.tmp_federated_site_info:
                self.tmp_federated_site_info[site_info["instance_name"]] = {}
                self.remote_conf_data["federated_form"]["from_previous_dag_run"] = None
                self.remote_conf_data["federated_form"][
                    "before_previous_dag_run"
                ] = None
            else:
                self.remote_conf_data["federated_form"]["before_previous_dag_run"] = (
                    self.tmp_federated_site_info[site_info["instance_name"]][
                        "before_previous_dag_run"
                    ]
                )
                self.remote_conf_data["federated_form"]["from_previous_dag_run"] = (
                    self.tmp_federated_site_info[site_info["instance_name"]][
                        "from_previous_dag_run"
                    ]
                )

            # create at local instance jobs for remote sites
            with requests.Session() as s:
                r = requests_retry_session(session=s).put(
                    f"{self.client_url}/workflow_jobs",
                    json={
                        "federated": True,
                        "dag_id": self.remote_conf_data["federated_form"][
                            "remote_dag_id"
                        ],
                        "conf_data": self.remote_conf_data,
                        "username": self.local_conf_data["workflow_form"]["username"],
                        "instance_names": [site_info["instance_name"]],
                        "workflow_id": self.local_conf_data["workflow_form"][
                            "workflow_id"
                        ],
                    },
                    verify=self.client_network["ssl_check"],
                )

            KaapanaFederatedTrainingBase.raise_kaapana_connection_error(r)
            print(f"Response r: {r}")
            response = r.json()
            print(f"Created Job and added to Workflow; Job: {response}")
            # print(f"Workflow: {response['workflow']}")
            self.tmp_federated_site_info[site_info["instance_name"]] = {
                "job_id": response[0]["id"],
                "fernet_key": site_info["fernet_key"],
            }

    @timeit
    def wait_for_jobs(self, federated_round):
        updated = {
            instance_name: False for instance_name in self.tmp_federated_site_info
        }
        # Waiting for updated files
        print("Waiting for updates")
        for idx in range(10000):
            if idx % 6 == 0:
                print(f"{10*idx} seconds")

            time.sleep(10)

            for instance_name, tmp_site_info in self.tmp_federated_site_info.items():
                with requests.Session() as s:
                    r = requests_retry_session(session=s).get(
                        f"{self.client_url}/job",
                        params={"job_id": tmp_site_info["job_id"]},
                        verify=self.client_network["ssl_check"],
                    )
                job = r.json()
                if job["status"] == "finished":
                    updated[instance_name] = True
                    tmp_site_info["before_previous_dag_run"] = job["conf_data"][
                        "federated_form"
                    ]["from_previous_dag_run"]
                    tmp_site_info["from_previous_dag_run"] = job["run_id"]
                elif job["status"] == "failed":
                    raise ValueError(
                        "A client job failed, interrupting, you can use the recovery_conf to continue your training, if there is an easy fix!"
                    )
            if np.sum(list(updated.values())) == len(self.remote_sites):
                break
        if bool(np.sum(list(updated.values())) == len(self.remote_sites)) is False:
            print("Update list")
            for k, v in updated.items():
                print(k, v)
            raise ValueError(
                "There are lacking updates, please check what is going on!"
            )

    @timeit
    def download_minio_objects_to_workflow_dir(
        self, federated_round, tmp_central_site_info
    ):
        project_bucket = self.remote_conf_data["project_form"]["s3_bucket"]
        if federated_round > 0:
            previous_federated_round_dir = os.path.join(
                self.remote_conf_data["federated_form"]["federated_dir"],
                str(federated_round - 1),
            )
        else:
            previous_federated_round_dir = None
        current_federated_round_dir = os.path.join(
            self.remote_conf_data["federated_form"]["federated_dir"],
            str(federated_round),
        )
        next_federated_round_dir = os.path.join(
            self.remote_conf_data["federated_form"]["federated_dir"],
            str(federated_round + 1),
        )
        # Downloading all objects
        for instance_name, tmp_site_info in tmp_central_site_info.items():
            tmp_site_info["file_paths"] = []
            tmp_site_info["next_object_names"] = []

            print(current_federated_round_dir)
            minio_client = self.minioSession.get_client()
            objects = minio_client.list_objects(
                project_bucket,
                os.path.join(current_federated_round_dir, instance_name),
                recursive=True,
            )
            for obj in objects:
                # https://github.com/minio/minio-py/blob/master/minio/datatypes.py#L103
                if (
                    obj.is_dir
                    or not obj.object_name.endswith(".tar")
                    or os.path.basename(obj.object_name).replace(".tar", "")
                    not in self.remote_conf_data["federated_form"][
                        "federated_operators"
                    ]
                    or "from_server" in obj.object_name
                ):
                    continue
                else:
                    file_path = os.path.join(
                        self.fl_working_dir,
                        os.path.relpath(
                            obj.object_name,
                            self.remote_conf_data["federated_form"]["federated_dir"],
                        ),
                    ).replace("/from_client", "")
                    file_dir = os.path.dirname(file_path)  # file_path.rsplit('/', 2)[0]
                    os.makedirs(file_dir, exist_ok=True)
                    minio_client = self.minioSession.get_client()
                    minio_client.fget_object(
                        project_bucket, obj.object_name, file_path
                    )
                    KaapanaFederatedTrainingBase.fernet_decryptfile(
                        file_path, tmp_site_info["fernet_key"]
                    )
                    KaapanaFederatedTrainingBase.apply_untar_action(file_path, file_dir)
                    tmp_site_info["file_paths"].append(file_path)
                    tmp_site_info["next_object_names"].append(
                        obj.object_name.replace(
                            current_federated_round_dir, next_federated_round_dir
                        )
                    )
            print("Removing objects from previous federated_round_dir on Minio")

            if previous_federated_round_dir is not None:
                minio_client = self.minioSession.get_client()
                minio_rmtree(
                    minio_client,
                    project_bucket,
                    os.path.join(previous_federated_round_dir, instance_name),
                )

    @abstractmethod
    @timeit
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
    def fed_avg(self, site_model_weights_dict=None):
        """
        FedAvg: Communication-efficient Learning of Deep networks from Decentralized Data (https://arxiv.org/abs/1602.05629)
        Sum model_weights up.
        Divide summed model_weights by num_sites.
        Return a site_model_weights_dict with always the same model_weights per site.

        Note:
        * perform averaging based on pointers on the dict keys obtained with .data_ptr()
        * solution from https://github.com/MIC-DKFZ/nnUNet/issues/2553
        * btw site_model_weights_dict looks like that: site_model_weights_dict = {"<siteA>": <model_weights_0> , "<siteB>": <model_weights_1>, ...}
        """

        # for sample-weighted aggregation, get number of samples per client and list of client_instance_names
        num_samples_per_client = dict()
        client_instance_names = []

        dataset_limit = self.remote_conf_data.get("data_form", {}).get(
            "dataset_limit", None
        )
        for site_idx, _ in enumerate(self.remote_sites):
            client_instance_names.append(self.remote_sites[site_idx]["instance_name"])
            dataset_name = self.remote_conf_data["data_form"]["dataset_name"]
            allowed_datasets = self.remote_sites[site_idx]["allowed_datasets"]
            identifiers = next(
                (
                    dataset["identifiers"]
                    for dataset in allowed_datasets
                    if dataset["name"] == dataset_name
                ),
                [],
            )
            num_identifiers_in_dataset = len(identifiers)
            num_samples_per_client[self.remote_sites[site_idx]["instance_name"]] = (
                num_identifiers_in_dataset
                if dataset_limit is None
                else (
                    num_identifiers_in_dataset
                    if num_identifiers_in_dataset < dataset_limit
                    else dataset_limit
                )
            )
        num_all_samples = sum(num_samples_per_client.values())
        print(
            f"Averaging model weights with client's dataset sizes: {num_samples_per_client} \
            and total number of samples of {num_all_samples}!"
        )

        # initialize network_weights with those of first client_instance
        list_of_network_parameters = list(site_model_weights_dict.values())
        network_weights = site_model_weights_dict[client_instance_names[0]]
        # get addresses of keys
        keys = list(network_weights.keys())
        address_key_dict = {}
        for k in keys:
            address = network_weights[k].data_ptr()
            if address not in address_key_dict.keys():
                address_key_dict[address] = [k]
            else:
                address_key_dict[address].append(k)

        # perform the fedavg
        for a in address_key_dict.keys():
            for client_instance_name, net in site_model_weights_dict.items():
                if client_instance_name == client_instance_names[0]:
                    # network weights of client_instance_names [0] are already in network_weights
                    # we still need to weight client 0's model params with it's dataset size
                    network_weights[address_key_dict[a][0]] = (
                        network_weights[address_key_dict[a][0]]
                        * num_samples_per_client[client_instance_name]
                    )
                else:
                    # weighted sum
                    network_weights[address_key_dict[a][0]] += (
                        net[address_key_dict[a][0]]
                        * num_samples_per_client[client_instance_name]
                    )
            # divided by num_all_samples
            network_weights[address_key_dict[a][0]] /= num_all_samples
            # modifying the 0th keys is sufficient as the other keys point to the same data

        # reformat to return
        return_model_weights_dict = collections.OrderedDict()
        for site in site_model_weights_dict.keys():
            return_model_weights_dict[site] = network_weights
        return return_model_weights_dict

    # @timeit
    def fed_dc(
        self,
        site_model_weights_dict=None,
        federated_round=None,
    ):
        """
        FedDC: Federated Learning from Small Datasets (https://arxiv.org/abs/2110.03469)
        Daisy chaining if (federated_round % dc_rate) == (dc_rate - 1).
        Aggregate local models if (federated_round % agg_rate) == (agg_rate - 1).

        Input:
        * site_model_weights_dict: site_model_weights_dict = {"<siteA>": <model_weights_0> , "<siteB>": <model_weights_1>, ...}
        * federated_round: current federated communication round
        * agg_rate: aggregation rate; defines how often local model weights are aggregated (avereaged)
        * dc_rate: daisy chaining rate; defines how often local models are randomly sent to other site

        Output:
        * return_model_weights_dict: with eiter just randomly permuted site keys or aggregated model_weights.
        """

        # do either daisy-chaining or aggregation
        if (federated_round % self.dc_rate) == (self.dc_rate - 1):
            # daisy chaining
            site_keys = list(site_model_weights_dict.keys())
            shuffled_site_keys = random.sample(site_keys, len(site_keys))
            return_model_weights_dict = dict(
                zip(
                    shuffled_site_keys,
                    [site_model_weights_dict[key] for key in shuffled_site_keys],
                )
            )
        if (federated_round % self.agg_rate) == (self.agg_rate - 1):
            # aggregation via FedAvg
            return_model_weights_dict = self.fed_avg(site_model_weights_dict)
        if ((federated_round % self.agg_rate) != (self.agg_rate - 1)) and (
            (federated_round % self.dc_rate) != (self.dc_rate - 1)
        ):
            raise ValueError(
                "Error while FedDC: Neither Daisy Chaining nor Aggregation was computed!"
            )
        return return_model_weights_dict

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

    @timeit
    def upload_workflow_dir_to_minio_object(
        self, federated_round, tmp_central_site_info
    ):
        # Push objects:
        for instance_name, tmp_site_info in tmp_central_site_info.items():
            for file_path, next_object_name in zip(
                tmp_site_info["file_paths"], tmp_site_info["next_object_names"]
            ):
                file_path = file_path.replace("/from_client", "")
                file_path = file_path.replace("/from_server", "")
                file_dir = file_path.replace(".tar", "")
                KaapanaFederatedTrainingBase.apply_tar_action(file_path, file_dir)
                KaapanaFederatedTrainingBase.fernet_encryptfile(
                    file_path, self.client_network["fernet_key"]
                )
                next_object_name = next_object_name.replace(
                    "from_client", "from_server"
                )
                print(f"Uploading {file_path } to {next_object_name}")
                minio_client = self.minioSession.get_client()
                minio_client.fput_object(
                    self.remote_conf_data["project_form"]["s3_bucket"],  # minio bucket
                    next_object_name,  # path in minio bucket
                    file_path,  # file in current workflow dir
                )
        print("Finished round", federated_round)

    @timeit
    def on_wait_for_jobs_end(self, federated_round):
        pass

    @timeit
    def central_steps(self, federated_round, tmp_central_site_info):
        # Working with downloaded objects
        self.download_minio_objects_to_workflow_dir(
            federated_round=federated_round, tmp_central_site_info=tmp_central_site_info
        )
        self.update_data(
            federated_round=federated_round, tmp_central_site_info=tmp_central_site_info
        )
        self.upload_workflow_dir_to_minio_object(
            federated_round=federated_round, tmp_central_site_info=tmp_central_site_info
        )

    @timeit
    def train_step(self, federated_round):
        if self.run_in_parallel is False:
            self.distribute_jobs(federated_round=federated_round)

        self.wait_for_jobs(federated_round=federated_round)
        tmp_central_site_info = {
            instance_name: tmp_site_info
            for instance_name, tmp_site_info in self.tmp_federated_site_info.items()
        }
        self.on_wait_for_jobs_end(federated_round=federated_round)
        self.create_recovery_conf(federated_round=federated_round)
        if (
            self.run_in_parallel is True
            and (federated_round + 1)
            < self.remote_conf_data["federated_form"]["federated_total_rounds"]
        ):
            self.distribute_jobs(federated_round=federated_round + 1)

        self.central_steps(
            federated_round=federated_round, tmp_central_site_info=tmp_central_site_info
        )

    def create_recovery_conf(self, federated_round):
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
            "workflow_form": {
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
            self.fl_working_dir, str(federated_round), "recovery_conf.json"
        )
        # os.makedirs(os.path.basename(recovery_path), exist_ok=True)
        os.makedirs(os.path.dirname(recovery_path), exist_ok=True)
        with open(recovery_path, "w", encoding="utf-8") as jsonData:
            json.dump(
                recovery_conf, jsonData, indent=2, sort_keys=True, ensure_ascii=True
            )

        minio_recovery_path = os.path.join(
            self.federated_dir,
            str(federated_round),
            "recovery_conf.json",
        )
        print(
            f"Uploading recovery_conf to MinIO: {self.remote_conf_data['project_form']['s3_bucket']}/{minio_recovery_path}"
        )
        minio_client = self.minioSession.get_client()
        minio_client.fput_object(
            self.remote_conf_data["project_form"]["s3_bucket"],  # minio bucket
            minio_recovery_path,  # path in minio bucket
            recovery_path,  # path of file in current workflow dir
        )

    @timeit
    def train(self):
        for federated_round in range(
            self.federated_round_start,
            self.remote_conf_data["federated_form"]["federated_total_rounds"],
        ):
            self.train_step(federated_round=federated_round)
            if federated_round > 0:
                previous_fl_working_round_dir = os.path.join(
                    self.fl_working_dir, str(federated_round - 1)
                )
                print(f"Removing previous round files {previous_fl_working_round_dir}")
                if os.path.isdir(previous_fl_working_round_dir):
                    shutil.rmtree(previous_fl_working_round_dir)

    def clean_up_minio(self):
        minio_client = self.minioSession.get_client()
        minio_rmtree(
            minio_client,
            self.remote_conf_data["project_form"]["s3_bucket"],
            self.remote_conf_data["federated_form"]["federated_dir"],
        )
