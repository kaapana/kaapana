import os
import time
import json
import shutil
import requests
import datetime

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

import torch
from torch import nn
from torch.nn import functional as F
from torchvision import transforms
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

from utilities import ClassifierMNIST, mnist_transforms


class Arguments():
    def __init__(self):
        self.run_id = os.environ['RUN_ID']
        self.workflow_dir = os.environ['WORKFLOW_DIR']
        self.data_path = os.path.join(os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])

        self.model_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'model')
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)

        self.model_cache = os.path.join(os.environ['WORKFLOW_DIR'], 'cache')
        if not os.path.exists(self.model_cache):
            os.makedirs(self.model_cache)
        
        self.procedure = os.getenv('PROCEDURE', 'avg')
        self.scheduler = os.getenv('SCHEDULER', '10.128.129.76')
        self.participants = json.loads(os.environ['PARTICIPANTS'])
        self.apply_tests = True
        self.checking_interval = 0.25 # minutes
        
        self.epochs = 1
        self.lr = 0.1
        self.batch_size = 32
        self.num_workers = 24


def prepare_dataloader_test(args):
    """Prepares dataloader for testing on central instance"""
    dataloader_test = DataLoader(
        dataset= ImageFolder(root=os.path.join(args.data_path, 'test'), transform=mnist_transforms['test']),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers
    )
    return dataloader_test


def test(model, dataloader_test, device):
    model.to(device)
    model.eval()
    test_loss, correct = 0, 0
    with torch.no_grad():
        for imgs, targets in dataloader_test:
            imgs, targets = imgs.to(device), targets.to(device)
            output = model(imgs)
            test_loss += F.nll_loss(output, targets, reduction='sum').item()    # sum up batch loss
            pred = output.argmax(dim=1, keepdim=True)                           # get the index of the max log-probability
            correct += pred.eq(targets.view_as(pred)).sum().item()
    
    test_loss /= len(dataloader_test.dataset)
    print('\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
        test_loss, correct, len(dataloader_test.dataset),
        100. * correct / len(dataloader_test.dataset)))


def apply_minio_action(action='put', run_dir='/data', bucket_name='federated-training', action_operator_dirs=['cache'], wait=True):
    """Calls service dag to apply action Minio/Airflow /data/model"""
    rest_call = {
        'rest_call': {
            'global': {},
            'operators': {
                'minio-actions-get': {
                    'action': action,
                    'run_dir': run_dir,
                    'bucket_name': bucket_name,
                    'action_operator_dirs': action_operator_dirs}}}}
    
    url='http://airflow-service.flow.svc:8080/flow/kaapana/api/trigger/service-minio-action'
    r = requests.post(url=url, json=rest_call, verify=False)
    print('Local Minio action ({})'.format(action), r.json())

    # wait until DAG was run
    if wait:
        time.sleep(60*0.5)


def model_to_minio(model, optimizer, action_operator_dirs=['model']):
    """Saves model with optimizer and puts them to Minio"""
    if not os.path.isdir(args.model_dir):
        os.mkdir(args.model_dir)    
    
    checkpoint = {
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict()
    }

    torch.save(checkpoint, os.path.join(args.model_dir, 'model_checkpoint.pt'))

    run_dir = '/data/{}'.format(args.run_id)
    apply_minio_action(action='put', run_dir=run_dir, action_operator_dirs=action_operator_dirs, wait=True)


def trigger_training_dag(participant, args):
    """Triggers Dag on training participant to train on its data"""

    dag_name = 'federated-training-mnist'
    
    # api call given to operator in remote dag
    recall = {
        'rest_call': {
            'global': {},
            'operators': {
                'minio-actions-get': {
                    'action': 'get',
                    'run_dir': '/data/{}'.format(args.run_id),
                    'bucket_name': 'federated-exp-mnist',
                    'action_operator_dirs': ['cache']
                }}}}
    
    # actual call to trigger dag
    rest_call = {
        'rest_call': {
            'global': {
                'bucket_name': 'federated-exp-mnist',
                'minio_host': args.scheduler},
            'operators': {
                'model-training': {
                    'host_ip': participant},
                'trigger-dag': {
                    'dag_host': args.scheduler,
                    'rest_call': recall }}}}

    url = 'https://{}/flow/kaapana/api/trigger/{}'.format(participant, dag_name)
    r = requests.post(url=url, json=rest_call, verify=False)
    print('Triggering Dag on {}'.format(participant), r.json())


def average_model_state_dicts(state_dicts):
    """Takes multiple state dicts to calculate their average """
    model_sd_avg = dict()
    for key in state_dicts[0]:
        model_sd_avg[key] = sum([state_dict[key] for state_dict in state_dicts]) / len(state_dicts)
    return model_sd_avg


def sequential_training(args):
    """Logic fof sequential model training"""

    # prepare dataloader if central testing is wanted
    if args.apply_tests:
        dataloader_test = prepare_dataloader_test(args)

    print('#'*10, 'START TRAINING - SEQUENTIAL TRAINING', '#'*10)
    print('#'*10, 'Using following participants: {}'.format(args.participants))
    
    for epoch in range(0, args.epochs):
        print('#'*10, 'EPOCH {}'.format(epoch))
        
        for participant in args.participants:
            print('#'*10, 'Training step on participant {}'.format(participant))

            # Clear airflow directories
            shutil.rmtree(args.model_dir)
            shutil.rmtree(args.model_cache)

            # trigger dag on participant - then wait until remote Dag recieved model
            trigger_training_dag(participant, args)
            time.sleep(60*1)

            # file path for next model checkpoint
            model_fp = os.path.join(args.model_cache, 'model_checkpoint_from_{}.pt'.format(participant))
            
            # wait + check if new model arrived in cache folder
            print('Keep waiting for model...')
            while not os.path.isfile(model_fp):
                time.sleep(60*args.checking_interval)
            
            print('Model recieved from participant {}'.format(participant))
            
            # load model and optimizer
            checkpoint = torch.load(model_fp)

            model = ClassifierMNIST()
            model.load_state_dict(checkpoint['model'])
            optimizer = torch.optim.SGD(model.parameters(), lr=args.lr)
            optimizer.load_state_dict(checkpoint['optimizer'])

            # test performance on local testing data
            if args.apply_tests:
                device = 'cpu'
                print('Testing model at current state using device: {}'.format(device))
                test(model, dataloader_test, device)
            
            # save new 'model_checkpoint.pt' to /model and put to local Minio
            model_to_minio(model, optimizer)

            # clear model cache
            apply_minio_action(action='remove', action_operator_dirs=['cache'], wait=False)
            print('')


def averaging_training(args):
    """Logic for federated averaging"""

    # prepare dataloader if central testing is wanted
    if args.apply_tests:
        dataloader_test = prepare_dataloader_test(args)

    print('#'*10, 'TRAINING START - MODEL AVERAGING', '#'*10)
    print('#'*10, 'Using following participants: {}'.format(args.participants))

    for epoch in range(0, args.epochs):
        print('#'*10, 'EPOCH {}'.format(epoch))
        
        # Clear airflow directories
        shutil.rmtree(args.model_dir)
        shutil.rmtree(args.model_cache)
        
        # trigger remote dags on participants
        print('#'*10, 'Distribute model to participants: {}'.format(args.participants))
        for participant in args.participants:
            trigger_training_dag(participant, args)

        model_file_list = [os.path.join(args.model_cache, f'model_checkpoint_from_{participant}.pt') for participant in args.participants]
        
        # wait until all models were send back to scheduler        
        print('Keep waiting for models...')
        while not all([os.path.isfile(model_fb) for model_fb in model_file_list]):
            time.sleep(60*args.checking_interval)

        print('Recieved models from all particpants ({})'.format(args.participants))

        # load state dicts & create new avg model
        model_state_dicts = [torch.load(model)['model'] for model in model_file_list]
        sd_avg = average_model_state_dicts(model_state_dicts)
        
        model_avg = ClassifierMNIST()
        model_avg.load_state_dict(sd_avg)

        optimizer = torch.optim.SGD(model_avg.parameters(), lr=args.lr)
        optimizer.load_state_dict(
            torch.load(model_file_list[0])['optimizer']
        )

        # test model on locally available test data
        if args.apply_tests:
            device = 'cpu'
            print('Testing averaged model at current state using device: {}'.format(device))
            test(model_avg, dataloader_test, device)
        
        # save new 'model_checkpoint.pt' to /model and put to local Minio
        model_to_minio(model_avg, optimizer)

        # clear local Minio model cache
        apply_minio_action(action='remove', run_dir=args.workflow_dir, action_operator_dirs=['cache'], wait=False)
        print('')


def main(args):

    # initialize classifier and put it to local Minio
    model = ClassifierMNIST()
    print('Put initial model to local Minio')
    model_to_minio(model, optimizer=torch.optim.SGD(model.parameters(), lr=args.lr))

    # select training procedure
    if args.procedure == 'avg':
        averaging_training(args)
    elif args.procedure == 'seq':
        sequential_training(args)
    else:
        raise AssertionError("Training procedure must be either 'avg' or 'seq'!")
    
    print('#'*10, 'TRAINING END', '#'*10)
    print('Final model can be found in Minio!\n')


if __name__ == '__main__':
    args = Arguments()
    main(args)