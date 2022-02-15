
import os
import functools
import json
import requests
import tarfile
from cryptography.fernet import Fernet

from minio import Minio

from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR



def update_job(federated, status, remote):
    if remote is True:
        r = requests.get('http://federated-backend-service.base.svc:5000/client/remote-kaapana-instance', params={'node_id': federated['node_id']})
        raise_kaapana_connection_error(r)
        kaapana_instance = r.json()
    else:
        r = requests.get('http://federated-backend-service.base.svc:5000/client/client-kaapana-instance')
        raise_kaapana_connection_error(r)
        kaapana_instance = r.json()
    kaapana_instance_url = f'{kaapana_instance["protocol"]}://{kaapana_instance["host"]}:{kaapana_instance["port"]}'
    ssl_check = kaapana_instance['ssl_check']
    if remote is True:
        r = requests.put(f'{kaapana_instance_url}/federated-backend/remote/job', verify=ssl_check, params={'job_id': federated['remote_job_id'], 'status': status}, headers={'FederatedAuthorization': kaapana_instance['token']})
        raise_kaapana_connection_error(r)
        print('Remote job updated!')
        print(r.json())
    else:
        r = requests.put('http://federated-backend-service.base.svc:5000/client/job', verify=False, params={'job_id': federated['client_job_id'], 'status': status})
        raise_kaapana_connection_error(r)
        print('Client job updated!')
        print(r.json())


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
        
def apply_tar_action(dst_filename, src_dir):
    print(f'Tar {src_dir} to {dst_filename}')
    with tarfile.open(dst_filename, "w:gz") as tar:
        tar.add(src_dir, arcname=os.path.basename(src_dir))

def apply_untar_action(src_filename, dst_dir):
    print(f'Untar {src_filename} to {dst_dir}')
    with tarfile.open(src_filename, "r:gz")as tar:
        tar.extractall(dst_dir)

def raise_kaapana_connection_error(r):
    if r.history:
        raise ConnectionError('You were redirect to the auth page. Your token is not valid!')
    try:
        r.raise_for_status()
    except:
        raise ValueError(f'Something was not okay with your request code {r}: {r.text}!')

def apply_minio_presigned_url_action(action, federated, operator_out_dir, root_dir):
    data = federated['minio_urls'][operator_out_dir][action]
    print(data)
    r = requests.get('http://federated-backend-service.base.svc:5000/client/remote-kaapana-instance', params={'node_id': federated['node_id']})
    raise_kaapana_connection_error(r)
    remote_network = r.json()
    print('Remote network')
    for k, v in remote_network.items():
        print(k, v)
    r = requests.get('http://federated-backend-service.base.svc:5000/client/client-kaapana-instance')
    raise_kaapana_connection_error(r)
    client_network = r.json()
    print('Client network')
    for k, v in client_network.items():
        print(k, v)

    minio_presigned_url = f'{remote_network["protocol"]}://{remote_network["host"]}:{remote_network["port"]}/federated-backend/remote/minio-presigned-url'
    ssl_check = remote_network["ssl_check"]
    filename = os.path.join(root_dir, os.path.basename(data['path'].split('?')[0]))
    if action == 'put':
        src_dir = os.path.join(root_dir, operator_out_dir)
        if not os.path.isdir(src_dir):
            raise ValueError(f'{src_dir} does not exist, you most probably try to push results on a batch-element level, however, so far only bach level output is supported for federated learning!')
        apply_tar_action(filename, src_dir)
        fernet_encryptfile(filename, client_network['fernet_key'])
        tar = open(filename, "rb")
        print(f'Putting {filename} to {remote_network}')
        r = requests.post(minio_presigned_url, verify=ssl_check, files={'file': tar}, headers={'FederatedAuthorization': remote_network['token'], 'presigned-url': data['path']})
        raise_kaapana_connection_error(r)

    if action == 'get':
        print(f'Getting {filename} from {remote_network}')
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with requests.get(minio_presigned_url, verify=ssl_check, stream=True, headers={'FederatedAuthorization': remote_network['token'], 'presigned-url': data['path']}) as r:
            raise_kaapana_connection_error(r)
            print(r.text)
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    #if chunk: 
                    f.write(chunk)
        fernet_decryptfile(filename, remote_network['fernet_key'])
        apply_untar_action(filename, os.path.join(root_dir))

    os.remove(filename)
    
                
def federated_action(operator_out_dir, action, dag_run_dir, federated):

    if federated['minio_urls'] is not None and operator_out_dir in federated['minio_urls']:
        apply_minio_presigned_url_action(action, federated, operator_out_dir, dag_run_dir)
#         HelperMinio.apply_action_to_object_dirs(minioClient, action, bucket_name=f'{federated["site"]}',
#                                 local_root_dir=dag_run_dir,
#                                 object_dirs=[operator_out_dir])

#######################



# Decorator
def federated_sharing_decorator(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
            
        # Same as in HelperCaching!
        if 'context' in kwargs:
            run_id = kwargs['context']['run_id']
            conf = kwargs['context']['dag_run'].conf
        elif type(args) == tuple and len(args) == 1 and "run_id" in args[0]:
            raise ValueError('Just to check if this case needs to be supported!', args, kwargs)
            run_id = args[0]['run_id']
        else:
            run_id = kwargs['run_id']
            conf =  kwargs["dag_run"].conf

        dag_run_dir = os.path.join(WORKFLOW_DIR, run_id)
        if conf is not None and 'federated' in conf and conf['federated'] is not None:
            federated = conf['federated']
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
                federated_action(self.operator_out_dir, 'get', dag_run_dir, federated)


        x = func(self, *args, **kwargs)
        if federated is not None and 'federated_operators' in federated and self.operator_out_dir in federated['federated_operators']:
            print('Putting data')
            federated_action(self.operator_out_dir, 'put', dag_run_dir, federated)

            if federated['federated_operators'].index(self.operator_out_dir) == 0:
                print('Updating the conf')
                conf['federated']['rounds'].append(conf['federated']['rounds'][-1] + 1) 
                conf['federated']['from_previous_dag_run'] = run_id
                os.makedirs(os.path.join(dag_run_dir, 'conf'), exist_ok=True)
                config_path = os.path.join(dag_run_dir, 'conf', 'conf.json')
                with open(config_path, "w", encoding='utf-8') as jsonData:
                    json.dump(conf, jsonData, indent=4, sort_keys=True, ensure_ascii=True)
                federated_action('conf', 'put', dag_run_dir, federated)
                update_job(federated, status='finished', remote=True)
                update_job(federated, status='finished', remote=False)

#                 HelperMinio.apply_action_to_file(minioClient, 'put', 
#                     bucket_name=f'{federated["site"]}', object_name='conf.json', file_path=config_path)
                # Implement removal of file?
#         #######################
        return x

    return wrapper