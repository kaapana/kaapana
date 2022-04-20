
import os
import shutil
import functools
import json
from pathlib import Path
import requests
import tarfile
from cryptography.fernet import Fernet


from minio import Minio

from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.blueprints.kaapana_utils import get_operator_properties, requests_retry_session

##### To be copied
def fernet_encryptfile(filepath, key):
    if key == 'deactivated':
        return
    fernet = Fernet(key.encode())
    with open(filepath, 'rb') as file:
        original = file.read()
    encrypted = fernet.encrypt(original)
    with open(filepath, 'wb') as encrypted_file:
        encrypted_file.write(encrypted)
        
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
def apply_tar_action(dst_filename, src_dir, whitelist_extensions_tuples=None):
    with tarfile.open(dst_filename, "w:gz" if dst_filename.endswith('gz') is True else "w") as tar:
        if whitelist_extensions_tuples is not None:
            for file_path in Path(src_dir).rglob('*'):
                if file_path.name.endswith(tuple(whitelist_extensions_tuples)):
                    tar.add(file_path, arcname=os.path.relpath(file_path, os.path.dirname(src_dir)), recursive=False)
        else:
            tar.add(src_dir, arcname=os.path.basename(src_dir))

def raise_kaapana_connection_error(r):
    if r.history:
        raise ConnectionError('You were redirect to the auth page. Your token is not valid!')
    try:
        r.raise_for_status()
    except:
        raise ValueError(f'Something was not okay with your request code {r}: {r.text}!')

def apply_minio_presigned_url_action(action, federated, operator_out_dir, root_dir, client_job_id, whitelist_federated_learning=None):
    data = federated['minio_urls'][operator_out_dir][action]
    with requests.Session() as s:
        r = requests_retry_session(session=s).get('http://federated-backend-service.base.svc:5000/client/job', params={'job_id': client_job_id})
    raise_kaapana_connection_error(r)
    client_job = r.json()
    print('Client job')
    print(json.dumps(client_job, indent=2))
    client_network  = client_job['kaapana_instance']
    print('Client network')
    print(json.dumps(client_network, indent=2))
    with requests.Session() as s:
        r = requests_retry_session(session=s).get('http://federated-backend-service.base.svc:5000/client/remote-kaapana-instance', params={'instance_name': client_job['addressed_kaapana_instance_name']})
    raise_kaapana_connection_error(r)
    remote_network = r.json()
    print('Remote network')
    print(json.dumps(remote_network, indent=2))

    minio_presigned_url = f'{remote_network["protocol"]}://{remote_network["host"]}:{remote_network["port"]}/federated-backend/remote/minio-presigned-url'
    ssl_check = remote_network["ssl_check"]
    filename = os.path.join(root_dir, os.path.basename(data['path'].split('?')[0]))
    if action == 'put':
        src_dir = os.path.join(root_dir, operator_out_dir)
        if not os.path.isdir(src_dir):
            raise ValueError(f'{src_dir} does not exist, you most probably try to push results on a batch-element level, however, so far only bach level output is supported for federated learning!')
        print(f'Tar {filename}')
        apply_tar_action(filename, src_dir, whitelist_federated_learning)
        print(f'Encrypting {filename}')
        fernet_encryptfile(filename, client_network['fernet_key'])
        with open(filename, "rb") as tar:
            print(f'Putting {filename} to {remote_network}')
            # with requests.post(minio_presigned_url, verify=ssl_check, files={'file': tar}, headers={'FederatedAuthorization': remote_network['token'], 'presigned-url': data['path']}) as r:
            #     raise_kaapana_connection_error(r)
            with requests.Session() as s:
                r = requests_retry_session(session=s, use_proxies=True).post(minio_presigned_url, verify=ssl_check, files={'file': tar}, headers={'FederatedAuthorization': remote_network['token'], 'presigned-url': data['path']})
                raise_kaapana_connection_error(r)
        print(f'Finished uploading {filename}!')
    if action == 'get':
        print(f'Getting {filename} from {remote_network}')
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with requests.Session() as s:
            with requests_retry_session(session=s, use_proxies=True).get(minio_presigned_url, verify=ssl_check, stream=True, headers={'FederatedAuthorization': remote_network['token'], 'presigned-url': data['path']}) as r:
                raise_kaapana_connection_error(r)
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): 
                        f.write(chunk)
        print(f'Decrypting {filename}')
        fernet_decryptfile(filename, remote_network['fernet_key'])
        print(f'Untar {filename}')
        apply_untar_action(filename, os.path.join(root_dir))
        print(f'Finished {filename}!')
    os.remove(filename)
    
                
def federated_action(operator_out_dir, action, dag_run_dir, federated, client_job_id, whitelist_federated_learning=None):

    if federated['minio_urls'] is not None and operator_out_dir in federated['minio_urls']:
        apply_minio_presigned_url_action(action, federated, operator_out_dir, dag_run_dir, client_job_id, whitelist_federated_learning)

#######################


# Decorator
def federated_sharing_decorator(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):

        max_retries = 10
        run_id, dag_run_dir, dag_run, downstream_tasks = get_operator_properties(*args, **kwargs)
        conf = dag_run.conf

        if conf is not None and 'federated_form' in conf and conf['federated_form'] is not None:
            federated = conf['federated_form']
            print('Federated config')
            print(federated)
        else:
            federated = None

        ##### To be copied
        if federated is not None and 'federated_operators' in federated and self.operator_out_dir in federated['federated_operators']:
            if self.allow_federated_learning is False:
                raise ValueError('The operator you want to use for federated learning does not allow federated learning, ' \
                'you will need to set the flag allow_federated_learning=True in order to permit the operator to be used in federated learning scenarios')
            if 'from_previous_dag_run' in federated and federated['from_previous_dag_run'] is not None:
                print('Downloading data from Minio')
                try_count = 0
                while try_count < max_retries:
                    print("Try: {}".format(try_count))
                    try_count += 1
                    try:
                        federated_action(self.operator_out_dir, 'get', dag_run_dir, federated, conf['client_job_id'])
                        break
                    except tarfile.ReadError as e:
                        print("The files was not downloaded properly...")
                        print("Trying again the download!")

                if try_count >= max_retries:
                    print("------------------------------------")
                    print("Max retries reached!")
                    print("------------------------------------")
                    raise ValueError("We were not able to download the file probarly!")



        x = func(self, *args, **kwargs)
    
        if federated is not None and 'federated_operators' in federated and self.operator_out_dir in federated['federated_operators']:
            print('Putting data')
            federated_action(self.operator_out_dir, 'put', dag_run_dir, federated, conf['client_job_id'], self.whitelist_federated_learning)

        return x

    return wrapper