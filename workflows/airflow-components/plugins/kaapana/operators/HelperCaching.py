
import os
import glob
import functools
import shutil
import json
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
    

def federated_action(operator_out_dir, action, dag_run_dir, federated, minioClient=None):


    dst = os.path.join(dag_run_dir, operator_out_dir)
    
    print(dst)
    if action == 'from_previous_dag_run':
        src = os.path.join(WORKFLOW_DIR, federated['from_previous_dag_run'], operator_out_dir)
        print(src)
        if os.path.isdir(src):
            print(f'Moving batch files from {src} to {dst}')
            shutil.move(src=src, dst=dst)
    else:
        print(f'Downloading data from Minio to {dst}')
        dst_root_dir = os.path.join(dag_run_dir, BATCH_NAME)
        print(os.path.join(dag_run_dir, BATCH_NAME), operator_out_dir)
        HelperMinio.apply_action_to_object_dirs(minioClient, action, bucket_name=f'{federated["site"]}',
                                local_root_dir=dag_run_dir,
                                object_dirs=[operator_out_dir])

    if action == 'from_previous_dag_run':
        src_root_dir = os.path.join(WORKFLOW_DIR, federated['from_previous_dag_run'], BATCH_NAME)
        dst_root_dir = os.path.join(dag_run_dir, BATCH_NAME)
        batch_folders = sorted([f for f in glob.glob(os.path.join(src_root_dir, '*'))])
        for batch_element_dir in batch_folders:
            src = os.path.join(batch_element_dir, operator_out_dir)
            rel_dir = os.path.relpath(src, src_root_dir)
            dst = os.path.join(dst_root_dir, rel_dir)
            print(os.path.isdir(src))
            print('dst', dst)
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

        print(federated)
        if federated is not None and 'federated_operators' in federated and self.name in federated['federated_operators']:
            minioClient = Minio(federated["minio_host"]+":"+federated["minio_port"],
                                access_key=federated["minio_access_key"],
                                secret_key=federated["minio_secret_key"],
                                secure=False)

        if federated is not None and 'from_previous_dag_run' in federated and federated['from_previous_dag_run'] is not None:
            if 'skip_operators' in federated and self.name in federated['skip_operators']:
                print('Skipping')
                return
            elif 'federated_operators' in federated and self.name in federated['federated_operators']:
                federated_action(self.operator_out_dir, 'get', dag_run_dir, federated, minioClient)
            else:
                federated_action(self.operator_out_dir, 'from_previous_dag_run', dag_run_dir, federated)
                print('Loaded from previous workflow')
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
        
        print(self.name)
        print(federated)
        if federated is not None and 'federated_operators' in federated and self.name in federated['federated_operators']:
            federated_action(self.operator_out_dir, 'put', dag_run_dir, federated, minioClient)

            print('Updating the conf')
            conf['federated']['rounds'].append(conf['federated']['rounds'][-1] + 1) 
            conf['federated']['from_previous_dag_run'] = run_id
            print(conf)
            config_path = os.path.join(dag_run_dir, 'conf.json')
            with open(config_path, "w", encoding='utf-8') as jsonData:
                json.dump(conf, jsonData, indent=4, sort_keys=True, ensure_ascii=True)
            HelperMinio.apply_action_to_file(minioClient, 'put', 
                bucket_name=f'{federated["site"]}', object_name='conf.json', file_path=config_path)
            # Implement removal of file?
            print('Updated the model!')    
        return x

    return wrapper