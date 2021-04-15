import os
import json
import requests

import torch
from torch.utils.data import Dataset, DataLoader

class OpenminedDataset(Dataset):
    '''Openmined Dataset using pointers to remote data instances'''
    
    def __init__(self, img_ptr, label_ptr):
        ''' '''
        self.img_ptr = img_ptr
        self.label_ptr = label_ptr
        self.transform = None
    
    def __len__(self):
        return len(self.img_ptr)

    def __getitem__(self, idx):
        '''Return image and corresponding label'''
        img_ptr = self.img_ptr[idx]
        label_ptr = self.label_ptr[idx]
        
        return img_ptr, label_ptr


class FederatedExperiment():
    """Base class for federated experiments (draft)"""
    def __init__(self, grid_host, grid_port):
        self.grid_host = grid_host
        self.grid_port = grid_port
        
        self.workers = None
        self.exp_tag = None

        self.model = None

    def run_experiment(self):
        """Iterate over epochs"""
        pass

    def train(self):
        """Traiing one epoch"""
        pass

    def _get_dataloaders(self):
        """Get data and targets to build dataloaders"""
        pass

    def shutdown_data_providers(self):
        """Shuts down all data provider used for this experiment"""
        for worker in self.workers.values():
            ip_worker = worker.address.split('//')[1].split(':')[0]    
            print(f'API call to shut down worker on machine {ip_worker}')
            shutdown_data_provider(ip=ip_worker, exp_tag=self.exp_tag)
    
    def save_model(self, save_model, model_name, out_dir):
        """Saves trained model - i.e. to minio"""
        if save_model:
            if not os.path.isdir(out_dir):
                os.mkdir(out_dir)
            path = '{}/{}_trained.pt'.format(out_dir, model_name)
            torch.save(self.model, path)
            print("Saved trained model as {}".format(path))


def shutdown_data_provider(ip, exp_tag):
    '''Calls API to shut down remote data-provider operator'''
    
    dag_id = 'openmined-provide-data'
    task_id = 'data-provider'
    airflow_api = f'https://{ip}/flow/kaapana/api'
    
    # get all dags
    r = requests.get(airflow_api + '/getdagruns', verify=False)
    dags_all = r.json()
    
    # extract relevant dags
    dags = [dag for dag in dags_all if \
            dag['dag_id'] == 'openmined-provide-data' and \
            dag['state'] == 'running' and \
            dag['conf']['rest_call']['operators']['data-provider']['exp_tag'] == exp_tag]
    
    # call Airlfow API: set data providing operator to success
    print('Mark data providing operator on machine {} as success'.format(ip))
    for dag in dags:
        run_id, state = dag['run_id'], 'success'
        url = airflow_api + f'/settaskstate/{dag_id}/{run_id}/{task_id}/{state}'
        
        r = requests.post(url, verify=False)
        print(r.json())
    
    # call Helm API: uninstall helm chart
    print('Uninstall Openmined node chart on machine {}'.format(ip))
    url = f'http://{ip}/kube-helm-api/helm-delete-chart?release_name=openmined-node'
    r =requests.get(url, verify=False)
    print(r.json())
