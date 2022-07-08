from argparse import Namespace
from cryptography.fernet import Fernet
import requests
import time
import numpy as np
import json
import os
import uuid
import shutil
import tarfile
import functools
from minio import Minio
from abc import ABC, abstractmethod
from requests.adapters import HTTPAdapter
from abc import ABC, abstractmethod
from minio.deleteobjects import DeleteObject
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Todo move in Jonas library as normal function 
def timeit(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        ts = time.time()
        x = func(self, *args, **kwargs)
        te = time.time()
        self.json_writer.append_data_dict({
            'name': func.__name__,
            'execution_time': te-ts,
            'timestamp': time.time(),
            'args': args,
            'kwargs': kwargs
        })
        return x
    return wrapper
    
# Todo move in Jonas library as normal function 
class JsonWriter(object):

    @staticmethod
    def _write_json(filename, data):
        with open(filename, 'w') as json_file:
            json.dump(data, json_file)
            
    @staticmethod
    def _load_json(filename):
        try:
            with open(filename) as json_file:
                exp_data = json.load(json_file)
        except FileNotFoundError:
            exp_data = []
        return exp_data

    def __init__(self, log_dir) -> None:
        self.filename = os.path.join(log_dir, 'fl_stats.json')
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        # not accumulating anything because this leads to a decrease in speed over many epochs!

    def append_data_dict(self, data_dict):
        exp_data = JsonWriter._load_json(self.filename)
        exp_data.append(data_dict)
        JsonWriter._write_json(self.filename, exp_data)

# Todo move in Jonas library as normal function 
def requests_retry_session(
    retries=16,
    backoff_factor=1,
    status_forcelist=[404, 429, 500, 502, 503, 504],
    session=None,
    use_proxies=False
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
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    if use_proxies is True:
        proxies = {
            'http': os.getenv('PROXY', None),
            'https': os.getenv('PROXY', None),
            'no_proxy': 'airflow-service.flow,airflow-service.flow.svc,' \
                'ctp-dicom-service.flow,ctp-dicom-service.flow.svc,'\
                    'dcm4chee-service.store,dcm4chee-service.store.svc,'\
                        'elastic-meta-service.meta,elastic-meta-service.meta.svc'\
                            'federated-backend-service.base,federated-backend-service.base.svc,' \
                                'minio-service.store,minio-service.store.svc'
        }
        print('Setting proxies', proxies)
        session.proxies.update(proxies)
    else:
        print('Not using proxies!')

    return session 

def minio_rmtree(minioClient, bucket_name, object_name):
    delete_object_list = map(
        lambda x: DeleteObject(x.object_name),
        minioClient.list_objects(bucket_name, object_name, recursive=True)
    )
    errors = minioClient.remove_objects(bucket_name, delete_object_list)
    for error in errors:
        raise NameError("Error occured when deleting object", error)

    
class KaapanaFederatedTrainingBase(ABC):


    # Todo move in Jonas library as normal function 
    @staticmethod
    def fernet_encryptfile(filepath, key):
        if key == 'deactivated':
            return
        fernet = Fernet(key.encode())
        with open(filepath, 'rb') as file:
            original = file.read()
        encrypted = fernet.encrypt(original)
        with open(filepath, 'wb') as encrypted_file:
            encrypted_file.write(encrypted)
    
    # Todo move in Jonas library as normal function 
    @staticmethod
    def fernet_decryptfile(filepath, key):
        if key == 'deactivated':
            return
        fernet = Fernet(key.encode())
        with open(filepath, 'rb') as enc_file:
            encrypted = enc_file.read()
        decrypted = fernet.decrypt(encrypted)
        with open(filepath, 'wb') as dec_file:
            dec_file.write(decrypted)

    # Todo move in Jonas library as normal function 
    def apply_untar_action(src_filename, dst_dir):
        print(f'Untar {src_filename} to {dst_dir}')
        with tarfile.open(src_filename, "r:gz" if src_filename.endswith('gz') is True else "r") as tar:
            tar.extractall(dst_dir)

    # Todo move in Jonas library as normal function             
    def apply_tar_action(dst_filename, src_dir):
        print(f'Tar {src_dir} to {dst_filename}')
        with tarfile.open(dst_filename, "w:gz" if dst_filename.endswith('gz') is True else "w") as tar:
            tar.add(src_dir, arcname=os.path.basename(src_dir))


    # Todo move in Jonas library as normal function 
    @staticmethod
    def raise_kaapana_connection_error(r):
        if r.history:
            raise ConnectionError('You were redirect to the auth page. Your token is not valid!')
        try:
            r.raise_for_status()
        except:
            raise ValueError(f'Something was not okay with your request code {r}: {r.text}!')
    
    def get_conf(self, workflow_dir=None):
        with open(os.path.join('/', workflow_dir, 'conf', 'conf.json'), 'r') as f:
            conf_data = json.load(f)
        if "external_schema_federated_form" not in conf_data:
            conf_data["external_schema_federated_form"] = {}
        if "federated_bucket" not in conf_data["external_schema_federated_form"]:
            conf_data["external_schema_federated_form"]["federated_bucket"] = conf_data["external_schema_federated_form"]["remote_dag_id"]
        if "federated_dir" not in conf_data["external_schema_federated_form"]:
            conf_data["external_schema_federated_form"]["federated_dir"] = self.federated_dir
        return conf_data

    def __init__(self, workflow_dir=None,
                 access_key='kaapanaminio',
                 secret_key='Kaapana2020',
                 minio_host='minio-service.store.svc',
                 minio_port='9000',
                 use_minio_mount=None
                ):
        
        self.use_minio_mount = use_minio_mount
        self.run_in_parallel = False
        self.federated_dir = os.getenv('RUN_ID', str(uuid.uuid4()))
        self.workflow_dir = workflow_dir or os.getenv('WORKFLOW_DIR', f'/kaapanasrc/data/federated-setup-central-test-220316153201233296')
        print('working directory', self.workflow_dir)

        conf_data = self.get_conf(self.workflow_dir)
        print(conf_data)

        self.remote_conf_data = {}
        self.local_conf_data = {}
        self.tmp_federated_site_info = {}
        print('Splitting conf data')
        for k, v in conf_data.items():
            if k.startswith('external_schema_'):
                self.remote_conf_data[k.replace('external_schema_', '')] = v
            elif k=='tmp_federated_site_info':
                self.tmp_federated_site_info =  v
            elif k in ["client_job_id", "x_auth_token"]:
                pass
            else:
                self.local_conf_data[k] = v


        if self.use_minio_mount is None:
            self.fl_working_dir = os.path.join('/', self.workflow_dir, os.getenv('OPERATOR_OUT_DIR', 'federated-operator'))
        else:
            self.fl_working_dir = os.path.join(self.use_minio_mount, self.remote_conf_data['federated_form']['remote_dag_id'], self.remote_conf_data['federated_form']['federated_dir'])
        print(self.fl_working_dir)

        self.json_writer = JsonWriter(log_dir=self.fl_working_dir)

        self.client_url = 'http://federated-backend-service.base.svc:5000/client'
        with requests.Session() as s:
            r = requests_retry_session(session=s).get(f'{self.client_url}/client-kaapana-instance')
        KaapanaFederatedTrainingBase.raise_kaapana_connection_error(r)
        self.client_network = r.json()

        if 'instance_names' in self.remote_conf_data:
            instance_names = self.remote_conf_data['instance_names']
        else:
            instance_names = []
        
        if 'federated_form' in self.remote_conf_data and 'federated_round' in self.remote_conf_data['federated_form']:
            self.federated_round_start = self.remote_conf_data['federated_form']['federated_round'] + 1
            print(f'Running in recovery mode and starting from round {self.federated_round_start}')
        else:
            self.federated_round_start = 0
        print(instance_names)
        with requests.Session() as s:
            r = requests_retry_session(session=s).post(f'{self.client_url}/get-remote-kaapana-instances', json={'instance_names': instance_names})
        KaapanaFederatedTrainingBase.raise_kaapana_connection_error(r)
        self.remote_sites = r.json()

        self.minioClient = Minio(
            minio_host+":"+minio_port,
            access_key=access_key,
            secret_key=secret_key,
            secure=False)

    @timeit
    def distribute_jobs(self, federated_round):
        # Starting round!
        self.remote_conf_data['federated_form']['federated_round'] = federated_round
        for site_info in self.remote_sites:
            if site_info['instance_name'] not in self.tmp_federated_site_info:
                self.tmp_federated_site_info[site_info['instance_name']] = {}
                self.remote_conf_data['federated_form']['from_previous_dag_run'] =  None
                self.remote_conf_data['federated_form']['before_previous_dag_run'] = None
            else:
                self.remote_conf_data['federated_form']['before_previous_dag_run'] = self.tmp_federated_site_info[site_info['instance_name']]['before_previous_dag_run']
                self.remote_conf_data['federated_form']['from_previous_dag_run'] = self.tmp_federated_site_info[site_info['instance_name']]['from_previous_dag_run']

            with requests.Session() as s:
                r = requests_retry_session(session=s).post(f'{self.client_url}/job', json={
                    "dag_id": self.remote_conf_data['federated_form']["remote_dag_id"],
                    "conf_data": self.remote_conf_data,
                    "status": "queued",
                    "addressed_kaapana_instance_name": self.client_network['instance_name'],
                    "kaapana_instance_id": site_info['id']}, verify=self.client_network['ssl_check'])

            KaapanaFederatedTrainingBase.raise_kaapana_connection_error(r)
            job = r.json()
            print('Created Job')
            print(job)
            self.tmp_federated_site_info[site_info['instance_name']] = {
                'job_id': job['id'],
                'fernet_key': site_info['fernet_key']
            }
    
    @timeit
    def wait_for_jobs(self, federated_round):
        updated = {instance_name: False for instance_name in self.tmp_federated_site_info}
        # Waiting for updated files
        print('Waiting for updates')
        for idx in range(10000):
            if idx%6 == 0:
                print(f'{10*idx} seconds')

            time.sleep(10)

            for instance_name, tmp_site_info in self.tmp_federated_site_info.items():
                with requests.Session() as s:
                    r = requests_retry_session(session=s).get(f'{self.client_url}/job', params={
                            "job_id": tmp_site_info["job_id"]
                        },  verify=self.client_network['ssl_check'])
                job = r.json()
                if job['status'] == 'finished':
                    updated[instance_name] = True
                    tmp_site_info['before_previous_dag_run'] = job['conf_data']['federated_form']['from_previous_dag_run']
                    tmp_site_info['from_previous_dag_run'] = job['run_id']
                elif job['status'] == 'failed':
                    raise ValueError('A client job failed, interrupting, you can use the recovery_conf to continue your training, if there is an easy fix!')
            if np.sum(list(updated.values())) == len(self.remote_sites):
                break
        if bool(np.sum(list(updated.values())) == len(self.remote_sites)) is False:
            print('Update list')
            for k, v in updated.items():
                print(k, v)
            raise ValueError('There are lacking updates, please check what is going on!')

    @timeit
    def download_minio_objects_to_workflow_dir(self, federated_round, tmp_central_site_info):
        federated_bucket = self.remote_conf_data['federated_form']['federated_bucket']
        if federated_round > 0:
            previous_federated_round_dir = os.path.join(self.remote_conf_data['federated_form']['federated_dir'], str(federated_round-1))
        else:
            previous_federated_round_dir = None    
        current_federated_round_dir = os.path.join(self.remote_conf_data['federated_form']['federated_dir'], str(federated_round))
        next_federated_round_dir =  os.path.join(self.remote_conf_data['federated_form']['federated_dir'], str(federated_round+1))
        # Downloading all objects
        for instance_name, tmp_site_info in tmp_central_site_info.items():
            tmp_site_info['file_paths'] = []
            tmp_site_info['next_object_names'] = []

            print(current_federated_round_dir)
            objects = self.minioClient.list_objects(federated_bucket, os.path.join(current_federated_round_dir, instance_name), recursive=True)
            for obj in objects:
                # https://github.com/minio/minio-py/blob/master/minio/datatypes.py#L103
                if obj.is_dir or not obj.object_name.endswith('.tar') or os.path.basename(obj.object_name).replace('.tar', '') not in self.remote_conf_data["federated_form"]["federated_operators"]:
                    continue
                else:
                    file_path = os.path.join(self.fl_working_dir, os.path.relpath(obj.object_name, self.remote_conf_data['federated_form']['federated_dir']))
                    file_dir = os.path.dirname(file_path)
                    os.makedirs(file_dir, exist_ok=True)
                    if self.use_minio_mount is None:
                        self.minioClient.fget_object(federated_bucket, obj.object_name, file_path)
                    KaapanaFederatedTrainingBase.fernet_decryptfile(file_path, tmp_site_info['fernet_key'])
                    KaapanaFederatedTrainingBase.apply_untar_action(file_path, file_dir)
                    tmp_site_info['file_paths'].append(file_path)
                    tmp_site_info['next_object_names'].append(obj.object_name.replace(current_federated_round_dir, next_federated_round_dir))
            print('Removing objects from previous federated_round_dir on Minio')

            if previous_federated_round_dir is not None and self.use_minio_mount is None:
                minio_rmtree(self.minioClient, federated_bucket, os.path.join(previous_federated_round_dir, instance_name))

    @abstractmethod
    @timeit
    def update_data(self, federated_round, tmp_central_site_info):
        pass

    @timeit
    def upload_workflow_dir_to_minio_object(self, federated_round, tmp_central_site_info):   
        # Push objects:
        for instance_name, tmp_site_info in tmp_central_site_info.items():
            for file_path, next_object_name in zip(tmp_site_info['file_paths'], tmp_site_info['next_object_names']):
                file_dir = file_path.replace('.tar', '')
                KaapanaFederatedTrainingBase.apply_tar_action(file_path, file_dir)
                KaapanaFederatedTrainingBase.fernet_encryptfile(file_path, self.client_network['fernet_key'])
                print(f'Uploading {file_path } to {next_object_name}')
                if self.use_minio_mount is None:
                    self.minioClient.fput_object(self.remote_conf_data['federated_form']['federated_bucket'], next_object_name, file_path)
                else:
                    dst = os.path.join(self.use_minio_mount, self.remote_conf_data['federated_form']['federated_bucket'], next_object_name)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copyfile(file_path, dst)
        print('Finished round', federated_round)

    @timeit
    def on_wait_for_jobs_end(self, federated_round):
        pass
    
    @timeit
    def central_steps(self, federated_round, tmp_central_site_info):
        # Working with downloaded objects
        self.download_minio_objects_to_workflow_dir(federated_round=federated_round, tmp_central_site_info=tmp_central_site_info)
        self.update_data(federated_round=federated_round, tmp_central_site_info=tmp_central_site_info)
        self.upload_workflow_dir_to_minio_object(federated_round=federated_round, tmp_central_site_info=tmp_central_site_info)

    @timeit
    def train_step(self, federated_round):

        if self.run_in_parallel is False:
            self.distribute_jobs(federated_round=federated_round)
        
        self.wait_for_jobs(federated_round=federated_round)
        tmp_central_site_info = { instance_name: tmp_site_info for instance_name, tmp_site_info in self.tmp_federated_site_info.items() }
        self.on_wait_for_jobs_end(federated_round=federated_round)
        self.create_recovery_conf(federated_round=federated_round)
        if self.run_in_parallel is True and (federated_round+1) < self.remote_conf_data['federated_form']['federated_total_rounds']:
            self.distribute_jobs(federated_round=federated_round+1)

        self.central_steps(federated_round=federated_round, tmp_central_site_info=tmp_central_site_info)

    def create_recovery_conf(self, federated_round):
        print('Recovery conf for round {}')
        self.tmp_federated_site_info = {instance_name: {k: tmp_site_info[k] for k in ['from_previous_dag_run', 'before_previous_dag_run']} for instance_name, tmp_site_info in self.tmp_federated_site_info.items()}
        recovery_conf = {
            "remote": False,
            "dag_id": os.getenv('DAG_ID'),
            "instance_names": [instance_name for instance_name, _ in self.tmp_federated_site_info.items()],
            "form_data": {
                **self.local_conf_data,
                **{f'external_schema_{k}' : v for k, v in self.remote_conf_data.items()},
                'tmp_federated_site_info': self.tmp_federated_site_info
                }
        }
        print('Recovery conf formatted')
        print(json.dumps(recovery_conf, indent=2))
        print('Recovery conf in one line')
        print(json.dumps(recovery_conf))
        recovery_path = os.path.join(self.fl_working_dir, str(federated_round), "recovery_conf.json")
        os.makedirs(os.path.basename(recovery_path), exist_ok=True)
        with open(recovery_path, "w", encoding='utf-8') as jsonData:
            json.dump(recovery_conf, jsonData, indent=2, sort_keys=True, ensure_ascii=True)


    @timeit    
    def train(self):
        for federated_round in range(self.federated_round_start, self.remote_conf_data['federated_form']['federated_total_rounds']):
            self.train_step(federated_round=federated_round)
            if federated_round > 0:
                previous_fl_working_round_dir = os.path.join(self.fl_working_dir, str(federated_round-1))
                print(f'Removing previous round files {previous_fl_working_round_dir}')
                if os.path.isdir(previous_fl_working_round_dir):
                    shutil.rmtree(previous_fl_working_round_dir)
        print('Cleaning up minio')

        if self.use_minio_mount is not None:
            dst = os.path.join('/', self.workflow_dir, os.getenv('OPERATOR_OUT_DIR', 'federated-operator'), os.path.basename(self.json_writer.filename))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(self.json_writer.filename, dst)

    def clean_up_minio(self):
        minio_rmtree(self.minioClient, self.remote_conf_data['federated_form']['federated_bucket'], self.remote_conf_data['federated_form']['federated_dir'])