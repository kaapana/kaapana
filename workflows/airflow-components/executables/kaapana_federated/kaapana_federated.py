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
from minio import Minio
from abc import ABC, abstractmethod
from requests.adapters import HTTPAdapter
from abc import ABC, abstractmethod
from minio.deleteobjects import DeleteObject
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Todo move in Jonas library as normal function 
def requests_retry_session(
    retries=15, # Retries for 18.2 hours
    backoff_factor=2,
    status_forcelist=[404, 429, 500, 502, 503, 504],
    session=None,
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
    @staticmethod
    def apply_tar_action(dst_filename, src_dir):
        print(f'Tar {src_dir} to {dst_filename}')
        with tarfile.open(dst_filename, "w:gz") as tar:
            tar.add(src_dir, arcname=os.path.basename(src_dir))

    # Todo move in Jonas library as normal function 
    @staticmethod
    def apply_untar_action(src_filename, dst_dir):
        print(f'Untar {src_filename} to {dst_dir}')
        with tarfile.open(src_filename, "r:gz")as tar:
            tar.extractall(dst_dir)
            
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
            conf_data["external_schema_federated_form"]["federated_dir"] = os.getenv('RUN_ID', str(uuid.uuid4())) 
        return conf_data

    def __init__(self, workflow_dir=None,
                 access_key='kaapanaminio',
                 secret_key='Kaapana2020',
                 minio_host='minio-service.store.svc',
                 minio_port='9000',
                ):
        
        workflow_dir = workflow_dir or os.getenv('WORKFLOW_DIR', f'/appdata/data/federated-setup-central-test-220316153201233296')
        print('working directory', workflow_dir)
        conf_data = self.get_conf(workflow_dir)
        print(conf_data)
        self.fl_working_dir = os.path.join('/', workflow_dir, os.getenv('OPERATOR_OUT_DIR', 'federated-operator'))
        
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

    
    @abstractmethod
    def update_data(self, federated_round):
        pass
    
    def distribute_jobs(self, federated_round):
        # Starting round!
        self.remote_conf_data['federated_form']['federated_round'] = federated_round
        for site_info in self.remote_sites:
            if federated_round == 0:
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
    def wait_for_jobs(self, federated_round):
        updated = {instance_name: False for instance_name in self.tmp_federated_site_info}
        # Waiting for updated files
        print('Waiting for updates')
        for idx in range(10000):
            if idx%6 == 0:
                print(f'{10*(idx+1)} seconds')

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
    
    def download_minio_objects_to_workflow_dir(self, federated_round):
        federated_bucket = self.remote_conf_data['federated_form']['federated_bucket']
        if federated_round > 0:
            previous_federated_round_dir = os.path.join(self.remote_conf_data['federated_form']['federated_dir'], str(federated_round-1))
        else:
            previous_federated_round_dir = None    
        current_federated_round_dir = os.path.join(self.remote_conf_data['federated_form']['federated_dir'], str(federated_round))
        next_federated_round_dir =  os.path.join(self.remote_conf_data['federated_form']['federated_dir'], str(federated_round+1))
        # Downloading all objects
        for instance_name, tmp_site_info in self.tmp_federated_site_info.items():
#             federated_bucket = self.remote_conf_data['federated_form']['federated_bucket']
#             if federated_round > 0:
#                 previous_federated_round_dir = os.path.join(self.remote_conf_data['federated_form']['federated_dir'], str(federated_round-1))
#             else:
#                 previous_federated_round_dir = None
#             current_federated_round_dir = os.path.join(self.remote_conf_data['federated_form']['federated_dir'], str(federated_round))
#             next_federated_round_dir =  os.path.join(self.remote_conf_data['federated_form']['federated_dir'], str(federated_round+1))
            
            tmp_site_info['file_paths'] = []
            tmp_site_info['next_object_names'] = []

            print(current_federated_round_dir)
            objects = self.minioClient.list_objects(federated_bucket, os.path.join(current_federated_round_dir, instance_name), recursive=True)
            for obj in objects:
                # https://github.com/minio/minio-py/blob/master/minio/datatypes.py#L103
                if obj.is_dir:
                    pass
                else:
                    file_path = os.path.join(self.fl_working_dir, os.path.relpath(obj.object_name, self.remote_conf_data['federated_form']['federated_dir']))
                    file_dir = os.path.dirname(file_path)
                    os.makedirs(file_dir, exist_ok=True)
                    self.minioClient.fget_object(federated_bucket, obj.object_name, file_path)
                    #self.minioClient.remove_object(federated_bucket, obj.object_name)
                    KaapanaFederatedTrainingBase.fernet_decryptfile(file_path, tmp_site_info['fernet_key'])
                    KaapanaFederatedTrainingBase.apply_untar_action(file_path, file_dir)
                    tmp_site_info['file_paths'].append(file_path)
                    tmp_site_info['next_object_names'].append(obj.object_name.replace(current_federated_round_dir, next_federated_round_dir))
            print('Removing objects from previous federated_round_dir on Minio')

            if previous_federated_round_dir is not None:
                minio_rmtree(self.minioClient, federated_bucket, os.path.join(previous_federated_round_dir, instance_name))
                
    def upload_workflow_dir_to_minio_object(self, federated_round):   
        # Push objects:
        for instance_name, tmp_site_info in self.tmp_federated_site_info.items():
            for file_path, next_object_name in zip(tmp_site_info['file_paths'], tmp_site_info['next_object_names']):
                file_dir = file_path.replace('.tar.gz', '')
                KaapanaFederatedTrainingBase.apply_tar_action(file_path, file_dir)
                KaapanaFederatedTrainingBase.fernet_encryptfile(file_path, self.client_network['fernet_key'])

    #                 next_object_name = obj.object_name.replace(current_federated_round_dir, next_federated_round_dir)
                print(f'Uploading {file_path } to {next_object_name}')
                self.minioClient.fput_object(self.remote_conf_data['federated_form']['federated_bucket'], next_object_name, file_path)

        print('Finished round', federated_round)
        
    def train_step(self, federated_round):
        self.distribute_jobs(federated_round)
        self.wait_for_jobs(federated_round)
        self.download_minio_objects_to_workflow_dir(federated_round)
        # Working with downloaded objects
        self.update_data(federated_round)
        self.upload_workflow_dir_to_minio_object(federated_round)  
    
    def train(self):
        for federated_round in range(self.federated_round_start, self.remote_conf_data['federated_form']['federated_total_rounds']):
            self.train_step(federated_round)
            print('Recovery conf')
            self.tmp_federated_site_info = {instance_name: {k: tmp_site_info[k] for k in ['from_previous_dag_run', 'before_previous_dag_run']} for instance_name, tmp_site_info in self.tmp_federated_site_info.items()}
            recovery_conf = {
                "remote": False,
                "dag_id": "Needs to be filled in manually, the dag_id of the ferederated dag!",
                "instance_names": ["Needs to be filled manully, your own instance_name!"],
                "form_data": {
                    **self.local_conf_data,
                    **{f'external_schema_{k}' : v for k, v in self.remote_conf_data.items()},
                    'tmp_federated_site_info': self.tmp_federated_site_info
                    }
            }
            print(json.dumps(recovery_conf, indent=2))
            with open(os.path.join(self.fl_working_dir, str(federated_round), "recovery_conf.json"), "w", encoding='utf-8') as jsonData:
                json.dump(recovery_conf, jsonData, indent=2, sort_keys=True, ensure_ascii=True)
            if federated_round > 0:
                previous_fl_working_round_dir = os.path.join(self.fl_working_dir, str(federated_round-1))
                print('Removing previous round files')
                if os.path.isdir(previous_fl_working_round_dir):
                    shutil.rmtree(previous_fl_working_round_dir)
        print('Cleaning up minio')
        minio_rmtree(self.minioClient, self.remote_conf_data['federated_form']['federated_bucket'], self.remote_conf_data['federated_form']['federated_dir'])