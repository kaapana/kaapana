from argparse import Namespace
from cryptography.fernet import Fernet
import requests
import time
import numpy as np
import json
import os
import tarfile
from minio import Minio
from abc import ABC, abstractmethod
from requests.adapters import HTTPAdapter
from abc import ABC, abstractmethod
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Todo move in Jonas library as normal function 
def requests_retry_session(
    retries=10,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
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
    
    @staticmethod
    def get_conf(dag_id, run_id, workflow_dir, federated_operators, skip_operators):
        with open(os.path.join('/', workflow_dir, 'conf', 'conf.json'), 'r') as f:
            conf_data = json.load(f)
        if "external_schema_federated_form" not in conf_data:
            conf_data["external_schema_federated_form"] = {}
        conf_data["external_schema_federated_form"].update({
            "federated_bucket": dag_id,
            "federated_dir": run_id,
            "federated_operators": federated_operators,
            "skip_operators": skip_operators
        })
        return conf_data

    def __init__(self, dag_id, conf_data, workflow_dir, federated_round_start=0,
                 access_key='kaapanaminio',
                 secret_key='Kaapana2020',
                 minio_host='minio-service.store.svc',
                 minio_port='9000',
                ):
        
        self.dag_id = dag_id
        self.fl_working_dir = os.path.join(workflow_dir, os.getenv('OPERATOR_OUT_DIR', 'federated-operator'))
        self.federated_round_start = federated_round_start
        self.remote_conf_data = {}
        self.local_conf_data = {}
        self.tmp_federated_site_infos = []
        for k, v in conf_data.items():
            if k.startswith('external_schema_'):
                self.remote_conf_data[k.replace('external_schema_', '')] = v
            else:
                self.local_conf_data[k] = v

        self.client_url = 'http://federated-backend-service.base.svc:5000/client'
        with requests.Session() as s:
            r = requests_retry_session(session=s).get(f'{self.client_url}/client-kaapana-instance')
        KaapanaFederatedTrainingBase.raise_kaapana_connection_error(r)
        self.client_network = r.json()

        if 'node_ids' in self.remote_conf_data:
            node_ids = self.remote_conf_data['node_ids']
        else:
            node_ids = []
        print(node_ids)
        with requests.Session() as s:
            r = requests_retry_session(session=s).post(f'{self.client_url}/get-remote-kaapana-instances', json={'node_ids': node_ids})
        KaapanaFederatedTrainingBase.raise_kaapana_connection_error(r)
        self.remote_sites = r.json()

        self.minioClient = Minio(
            minio_host+":"+minio_port,
            access_key=access_key,
            secret_key=secret_key,
            secure=False)

    
    @abstractmethod
    def update_data(self, tmp_federated_site_info, federated_round):
        pass
    
    def distribute_jobs(self, tmp_federated_site_info, federated_round):
        # Starting round!
        self.remote_conf_data['federated_form']['federated_round'] = federated_round

        for site_info in self.remote_sites:
            if federated_round == 0:
                tmp_federated_site_info[site_info['node_id']] = {}
                self.remote_conf_data['federated_form']['from_previous_dag_run'] =  None
            else:
                self.remote_conf_data['federated_form']['from_previous_dag_run'] = tmp_federated_site_info[site_info['node_id']]['from_previous_dag_run']

            with requests.Session() as s:
                r = requests_retry_session(session=s).post(f'{self.client_url}/job', json={
                    "dag_id": self.dag_id,
                    "conf_data": self.remote_conf_data,
                    "status": "queued",
                    "addressed_kaapana_node_id": self.client_network['node_id'],
                    "kaapana_instance_id": site_info['id']}, verify=self.client_network['ssl_check'])

            KaapanaFederatedTrainingBase.raise_kaapana_connection_error(r)
            job = r.json()
            print('Created Job')
            print(job)
            tmp_federated_site_info[site_info['node_id']] = {
                'job_id': job['id'],
                'fernet_key': site_info['fernet_key']
            }
    def wait_for_jobs(self, tmp_federated_site_info, federated_round):
        updated = {node_id: False for node_id in tmp_federated_site_info}
        # Waiting for updated files
        print('Waiting for updates')
        for idx in range(10000):
            if idx%6 == 0:
                print(f'{10*(idx+1)} seconds')

            time.sleep(10) 
            for node_id, tmp_site_info in tmp_federated_site_info.items():
                with requests.Session() as s:
                    r = requests_retry_session(session=s).get(f'{self.client_url}/job', params={
                            "job_id": tmp_site_info["job_id"]
                        },  verify=self.client_network['ssl_check'])
                job = r.json()
                #print(json.dumps(job, indent=2))
#                     print(job['status'])
#                     print(job['run_id'])
#                     print(job['description'])
#                     print(job['conf_data']['federated_form']['from_previous_dag_run'])
                if job['status'] == 'finished':
                    updated[node_id] = True
                    tmp_site_info['from_previous_dag_run'] = job['run_id']
            if np.sum(list(updated.values())) == len(self.remote_sites):
                break
        if bool(np.sum(list(updated.values())) == len(self.remote_sites)) is False:
            print('Update list')
            for k, v in updated.items():
                print(k, v)
            raise ValueError('There are lacking updates, please check what is going on!')
    
    def download_minio_objects_to_workflow_dir(self, tmp_federated_site_info, federated_round):
        # Downloading all objects
        for node_id, tmp_site_info in tmp_federated_site_info.items():
            tmp_site_info['file_paths'] = []
            tmp_site_info['next_object_names'] = []
            current_federated_round_dir = os.path.join(self.remote_conf_data['federated_form']['federated_dir'], str(federated_round))
            next_federated_round_dir =  os.path.join(self.remote_conf_data['federated_form']['federated_dir'], str(federated_round+1))
            print(current_federated_round_dir)
            objects = self.minioClient.list_objects(
                self.remote_conf_data['federated_form']['federated_bucket'], os.path.join(current_federated_round_dir, node_id), recursive=True)
            for obj in objects:
                # https://github.com/minio/minio-py/blob/master/minio/datatypes.py#L103
                if obj.is_dir:
                    pass
                else:
                    file_path = os.path.join(self.fl_working_dir, os.path.relpath(obj.object_name, self.remote_conf_data['federated_form']['federated_dir']))
                    file_dir = os.path.dirname(file_path)
                    os.makedirs(file_dir, exist_ok=True)
                    self.minioClient.fget_object(self.remote_conf_data['federated_form']['federated_bucket'], obj.object_name, file_path)
                    self.minioClient.remove_object(self.remote_conf_data['federated_form']['federated_bucket'], obj.object_name)
                    KaapanaFederatedTrainingBase.fernet_decryptfile(file_path, tmp_site_info['fernet_key'])
                    KaapanaFederatedTrainingBase.apply_untar_action(file_path, file_dir)
                    tmp_site_info['file_paths'].append(file_path)
                    tmp_site_info['next_object_names'].append(obj.object_name.replace(current_federated_round_dir, next_federated_round_dir))
        return tmp_federated_site_info
    
    def upload_workflow_dir_to_minio_object(self, tmp_federated_site_info, federated_round):   
        # Push objects:
        for node_id, tmp_site_info in tmp_federated_site_info.items():
            for file_path, next_object_name in zip(tmp_site_info['file_paths'], tmp_site_info['next_object_names']):
                file_dir = file_path.replace('.tar.gz', '')
                KaapanaFederatedTrainingBase.apply_tar_action(file_path, file_dir)
                KaapanaFederatedTrainingBase.fernet_encryptfile(file_path, tmp_site_info['fernet_key'])

    #                 next_object_name = obj.object_name.replace(current_federated_round_dir, next_federated_round_dir)
                print(f'Uploading {file_path } to {next_object_name}')
                self.minioClient.fput_object(self.remote_conf_data['federated_form']['federated_bucket'], next_object_name, file_path)

        print('Finished round', federated_round)
        
    def train_step(self, tmp_federated_site_info, federated_round):
        self.distribute_jobs(tmp_federated_site_info, federated_round)
        self.wait_for_jobs(tmp_federated_site_info, federated_round)
        self.download_minio_objects_to_workflow_dir(tmp_federated_site_info, federated_round)
        # Working with downloaded objects
        self.update_data(tmp_federated_site_info, federated_round)
        self.upload_workflow_dir_to_minio_object(tmp_federated_site_info, federated_round)
        return tmp_federated_site_info
    def train(self):
        tmp_federated_site_info = {}
        print(self.remote_conf_data)
        for federated_round in range(self.federated_round_start, self.remote_conf_data['federated_form']['federated_total_rounds']):
            tmp_federated_site_info = self.train_step(tmp_federated_site_info, federated_round)
            self.tmp_federated_site_infos.append({node_id: {k: tmp_site_info[k] for k in ['from_previous_dag_run']} for node_id, tmp_site_info in tmp_federated_site_info.items()})