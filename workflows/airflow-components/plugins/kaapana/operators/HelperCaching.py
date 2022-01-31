
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

        if 'context' in kwargs:
            run_id = kwargs['context']['run_id']
        elif type(args) == tuple and len(args) == 1 and "run_id" in args[0]:
            run_id = args[0]['run_id']
        else:
            run_id = kwargs['run_id']

        dag_run_dir = os.path.join(WORKFLOW_DIR, run_id)
        
        federated = None
        if 'context' in kwargs:
            print(kwargs)
            print(kwargs['context'])
        else:
            print('caching kwargs', kwargs["dag_run"].conf)
            conf =  kwargs["dag_run"].conf
            if kwargs["dag_run"] is not None and conf is not None and 'federated' in conf and conf['federated'] is not None:
                federated = conf['federated']

        if federated is not None and 'from_previous_dag_run' in federated and federated['from_previous_dag_run'] is not None:
            if 'skip_operators' in federated and self.name in federated['skip_operators']:
                print('Skipping')
                return
            elif 'federated_operators' in federated and self.name in federated['federated_operators']:
                pass
            else:
                print(f'Copying data from previous workflow for {self.name}')
                from_previous_dag_run_action(self.operator_out_dir, 'from_previous_dag_run', dag_run_dir, federated)
                return


        if self.manage_cache == 'overwrite' or self.manage_cache == 'clear':
            cache_action(cache_operator_dirs, 'remove', dag_run_dir)
            print('Clearing cache')

        if self.manage_cache == 'cache':
            if cache_action(cache_operator_dirs, 'get', dag_run_dir) is True:
                print(f'{", ".join(cache_operator_dirs)} output loaded from cache')
                return
        
        x = func(self, *args, **kwargs)
        if self.manage_cache  == 'cache' or self.manage_cache == 'overwrite':
            cache_action(cache_operator_dirs, 'put', dag_run_dir)
            print(f'{", ".join(cache_operator_dirs)} output saved to cache')
        else:
            print('Caching is not used!')
        return x

    return wrapper