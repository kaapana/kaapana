
import os
import glob
import functools
import shutil
import json
import requests
import tarfile
import gzip

from minio import Minio

from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.operators.HelperMinio import HelperMinio
from kaapana.operators.HelperFederated import raise_kaapana_connection_error
from kaapana.blueprints.kaapana_utils import get_operator_properties, requests_retry_session

def update_job(client_job_id, status, run_id=None, description=None):
    with requests.Session() as s:
        r = requests_retry_session(session=s).get('http://federated-backend-service.base.svc:5000/client/job', params={'job_id': client_job_id})
    raise_kaapana_connection_error(r)
    client_job = r.json()

    with requests.Session() as s:
        r = requests_retry_session(session=s).put('http://federated-backend-service.base.svc:5000/client/job', verify=False, json={
            'job_id': client_job_id, 
            'status': status,
            'run_id': run_id,
            'description': description,
            'addressed_kaapana_node_id': client_job['addressed_kaapana_node_id'],
            'external_job_id': client_job['external_job_id']
        })
    raise_kaapana_connection_error(r)
    print('Client job updated!')
    print(r.json())

def cache_action(cache_operator_dirs, action, dag_run_dir):
    loaded_from_cache = True
    batch_folders = sorted([f for f in glob.glob(os.path.join(dag_run_dir, BATCH_NAME, '*'))])
    if not batch_folders:
        loaded_from_cache=False

    local_root_dir = os.path.join(dag_run_dir, BATCH_NAME)
    for batch_element_dir in batch_folders:
        for cache_operator_dir in cache_operator_dirs:
            element_output_dir = os.path.join(batch_element_dir, cache_operator_dir)
            rel_dir = os.path.relpath(element_output_dir, local_root_dir)
            rel_dir = '' if rel_dir== '.' else rel_dir
            object_dirs = [rel_dir]
            HelperMinio.apply_action_to_object_dirs(HelperMinio.minioClient, action, 'cache', local_root_dir, object_dirs=object_dirs)
            try:
                if len(os.listdir(element_output_dir)) == 0:
                    loaded_from_cache = False
            except FileNotFoundError:
                loaded_from_cache = False 
    return loaded_from_cache

def from_previous_dag_run_action(operator_out_dir, action, dag_run_dir, federated):

    if action == 'from_previous_dag_run':
        src = os.path.join(WORKFLOW_DIR, federated['from_previous_dag_run'], operator_out_dir)
        print(src)
        dst = os.path.join(dag_run_dir, operator_out_dir)
        print(dst)
        if os.path.isdir(src):
            print(f'Moving batch files from {src} to {dst}')
            shutil.move(src=src, dst=dst)

    if action == 'from_previous_dag_run':
        src_root_dir = os.path.join(WORKFLOW_DIR, federated['from_previous_dag_run'], BATCH_NAME)
        dst_root_dir = os.path.join(dag_run_dir, BATCH_NAME)
        batch_folders = sorted([f for f in glob.glob(os.path.join(src_root_dir, '*'))])
        for batch_element_dir in batch_folders:
            src = os.path.join(batch_element_dir, operator_out_dir)
            rel_dir = os.path.relpath(src, src_root_dir)
            dst = os.path.join(dst_root_dir, rel_dir)
            if os.path.isdir(src):
                print(f'Moving batch element files from {src} to {dst}')
                shutil.move(src=src, dst=dst)

# Decorator
def cache_operator_output(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):

        cache_operator_dirs = [self.operator_out_dir]
        if self.manage_cache not in ['ignore', 'cache', 'overwrite', 'clear']:
            raise AssertionError("Invalid name '{}' for manage_cache. It must be set to None, 'ignore', 'cache', 'overwrite' or 'clear'".format(self.manage_cache))

        # # Same as in HelperFederated!
        # if 'context' in kwargs:
        #     run_id = kwargs['context']['run_id']
        #     conf = kwargs['context']['dag_run'].conf
        # elif type(args) == tuple and len(args) == 1 and "run_id" in args[0]:
        #     raise ValueError('Just to check if this case needs to be supported!', args, kwargs)
        #     run_id = args[0]['run_id']
        # else:
        #     run_id = kwargs['run_id']
        #     conf =  kwargs["dag_run"].conf

        # dag_run_dir = os.path.join(WORKFLOW_DIR, run_id)

        run_id, dag_run_dir, conf = get_operator_properties(*args, **kwargs)

        if conf is not None and 'client_job_id' in conf:
            update_job(conf['client_job_id'], status='running', run_id=run_id, description=f'Running the operator {self.name}')
        
        if conf is not None and 'federated_form' in conf and conf['federated_form'] is not None:
            federated = conf['federated_form']
            print('Federated config')
            print(federated)
            last_round = 'federated_total_rounds' in federated and 'federated_round' in federated and int(federated['federated_total_rounds']) == (int(federated['federated_round'])+1)
            print('Last round', last_round)
            omit_from_previous_dag_run= False
        else:
            federated = None

        if federated is not None and 'skip_operators' in federated and self.operator_out_dir in federated['skip_operators']:
            if last_round is False:
                print('Skipping')
                return
            else:
                omit_from_previous_dag_run = True

        if federated is not None and 'from_previous_dag_run' in federated and federated['from_previous_dag_run'] is not None:
            if 'federated_operators' in federated and self.operator_out_dir in federated['federated_operators']:
                pass
            elif omit_from_previous_dag_run is True:
                pass
                print(f"Ignoring from_previous_dag_run_action for opperators since we are in the last round and we are part of the skip_operators...")
            else:
                print(f'Copying data from previous workflow for {self.operator_out_dir}')
                from_previous_dag_run_action(self.operator_out_dir, 'from_previous_dag_run', dag_run_dir, federated)
                return


        if self.manage_cache == 'overwrite' or self.manage_cache == 'clear':
            cache_action(cache_operator_dirs, 'remove', dag_run_dir)
            print('Clearing cache')

        if self.manage_cache == 'cache':
            if cache_action(cache_operator_dirs, 'get', dag_run_dir) is True:
                print(f'{", ".join(cache_operator_dirs)} output loaded from cache')
                return

        try:
            x = func(self, *args, **kwargs)
        except Exception as e:
            if conf is not None and 'client_job_id' in conf:
                update_job(conf['client_job_id'], status='failed', run_id=run_id, description=f'Operator {self.name} had an exception {e}')
            raise e

        if self.manage_cache  == 'cache' or self.manage_cache == 'overwrite':
            cache_action(cache_operator_dirs, 'put', dag_run_dir)
            print(f'{", ".join(cache_operator_dirs)} output saved to cache')
        else:
            print('Caching is not used!')

        return x

    return wrapper