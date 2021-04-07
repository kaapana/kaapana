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


class Arguments():
    def __init__(self):
        self.participants = os.getenv('PARTICIPANTS', )
        self.data_path = os.path.join(os.environ["WORKFLOW_DIR"], os.environ['OPERATOR_IN_DIR'])
        self.test_data_dir = os.path.join(self.data_path, 'test')

        self.scheduler = '10.128.129.76'
        self.model_dir = 'models/model'
        self.model_cache = os.getenv('MODELS_CACHE', 'models/cache')
        if not os.path.exists(self.model_cache):
            os.makedirs(self.model_cache)

        self.checking_interval = 0.25 # minutes
        self.apply_tests = True

        self.epochs = 3
        self.lr = 0.1
        self.batch_size = 32
        self.num_workers = 24


class ClassifierMNIST(nn.Module):
    def __init__(self):
        super(ClassifierMNIST, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.fc1 = nn.Linear(9216, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2)
        x = torch.flatten(x, 1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)


def prepare_dataloader_test(args):
    """Prepares dataloader for testing on central instance"""
    mnist_transform = transforms.Compose([
        transforms.Grayscale(num_output_channels=1), # <-- needed since imgs are loaded with 3 channels by default
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
        ])
    
    dataloader_test = DataLoader(
        dataset= ImageFolder(root=args.test_data_dir, transform=mnist_transform),
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
            test_loss += F.nll_loss(output, targets, reduction='sum').item() # sum up batch loss
            pred = output.argmax(dim=1, keepdim=True) # get the index of the max log-probability
            correct += pred.eq(targets.view_as(pred)).sum().item()
    
    test_loss /= len(dataloader_test.dataset)
    print('\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
        test_loss, correct, len(dataloader_test.dataset),
        100. * correct / len(dataloader_test.dataset)))


def apply_minio_action(action='put', run_dir='/models', bucket_name='federated-training', action_operator_dirs=['cache'], wait=True):
    """Calls service dag to apply action Minio/Airflow /models/model"""
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

    if wait: # wait until DAG was run
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
    apply_minio_action(action='put', wait=True, action_operator_dirs=action_operator_dirs)


def trigger_training_dag(participant, args):
    """Triggers Dag on training participant to train on its data"""
    rest_call = {
        'rest_call': {
            'global': {
                'bucket_name': 'federated-training',
                'minio_host': args.scheduler},
            'operators': {
                'model-training': {
                    'host_ip': participant},
                'trigger-remote-dag': {
                    'dag_host': args.scheduler }}}}

    url = 'https://{}/flow/kaapana/api/trigger/federated-exp-train-step-mnist'.format(participant)
    r = requests.post(url=url, json=rest_call, verify=False)
    print('Triggering Dag on {}'.format(participant), r.json())


def average_model_state_dicts(state_dicts):
    """Takes multiple state dicts to calculate their average """
    model_sd_avg = dict()
    for key in state_dicts[0]:
        model_sd_avg[key] = sum([state_dict[key] for state_dict in state_dicts]) / len(state_dicts)
    return model_sd_avg


def main(args):

    # initialize classifier and put it to local Minio
    model = ClassifierMNIST()
    print('Put initial model to local Minio')
    model_to_minio(model, optimizer=torch.optim.SGD(model.parameters(), lr=args.lr))

    # prepare dataloader if central testing is wanted
    if args.apply_tests:
        dataloader_test = prepare_dataloader_test(args)
    
    participants = ['10.128.129.41', '10.128.129.6', '10.128.130.197'] # args.participants

    print('#'*10, 'START TRAINING', '#'*10)
    print('#'*10, 'Using following participants: {}'.format(participants))

    for epoch in range(0, args.epochs):
        print('#'*10, 'EPOCH {}'.format(epoch))
        
        # Clear airflow directories
        shutil.rmtree(args.model_dir)
        shutil.rmtree(args.model_cache)
        
        # trigger remote dags on participants
        print('#'*10, 'Distribute model to participants: {}'.format(participants))
        for participant in participants:
            trigger_training_dag(participant, args)

        model_file_list = [os.path.join(args.model_cache, f'model_checkpoint_from_{participant}.pt') for participant in participants]
        
        # wait until all models were send back to scheduler        
        print('Keep waiting for models...')
        while True:
            time.sleep(60*args.checking_interval)
            models_available = [os.path.isfile(model_fb) for model_fb in model_file_list]
            
            if all(models_available):
                break
        print('Revieved models from all particpants ({})'.format(participants))

        # load state dicts & create new avg model
        model_state_dicts = [torch.load(model)['model'] for model in model_file_list]
        sd_avg = average_model_state_dicts(model_state_dicts)
        
        model_avg = ClassifierMNIST()
        model_avg.load_state_dict(sd_avg)

        optimizer = torch.optim.SGD(model.parameters(), lr=args.lr)
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
        apply_minio_action(action='remove', action_operator_dirs=['cache'], wait=False)
    
    print('')
    print('#'*10, 'END TRAINING', '#'*10)
    print('Final model can be found in Minio!\n')


if __name__ == '__main__':
    args = Arguments()
    main(args)