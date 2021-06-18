import os
import json
import time
import shutil
from datetime import datetime

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

from utilities import (
    ClassifierMNIST,
    mnist_transforms,
    average_model_state_dicts,
    save_checkpoints_before_avg,
    save_checkpoint
)


class Arguments():
    def __init__(self):
        
        # control what is done in this script
        self.initialize_model = (os.environ.get('INIT_MODEL', 'False') == 'True')
        self.inference = (os.environ.get('INFERENCE', 'False') == 'True')
        self.procedure = os.environ.get('PROCEDURE')
        
        self.workflow_dir = os.environ['WORKFLOW_DIR']
        
        # model where processed/averaged model is saved
        self.model_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'model')
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
        
        # directory where incoming models are saved (by workers)
        self.model_cache = os.path.join(os.environ['WORKFLOW_DIR'], 'cache')
        if not os.path.exists(self.model_cache):
            os.makedirs(self.model_cache)
        
        # local directory for model checkpoints
        self.checkpoints_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'checkpoints')
        if not os.path.exists(self.checkpoints_dir):
            os.makedirs(self.checkpoints_dir)
        
        # timestamp logging
        self.logging = '/models/logging'
        if not os.path.exists(self.logging):
            os.makedirs(self.logging)
        
        # data with test data (i.e for global inference)
        if self.inference:
            self.data_dir = os.path.join(os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
        
        # federated training
        self.fed_rounds_total = os.environ['FED_ROUNDS_TOTAL']
        self.fed_round = int(os.environ['FED_ROUND']) if os.environ['FED_ROUND'] != 'None' else 0
        self.participants = json.loads('{}'.format(os.environ["PARTICIPANTS"].replace("'", '"'))) if os.environ["PARTICIPANTS"] != 'None' else None # enabels to parse a list as env
        
        self.worker = os.environ['WORKER']
        if self.procedure == 'seq' and self.worker == 'None':
            self.worker = self.participants[0]

        # training parameters
        self.lr_initial = float(os.environ['LEARNING_RATE']) if os.environ['LEARNING_RATE'] != 'None' else 0.1


def inference(model_dir, data_dir, **kwargs):
    """Applies federated trained model on test data"""
    print('#####', 'Inference', '#####')

    # load trained model
    print('Loading trained model')
    model = ClassifierMNIST()
    model.load_state_dict(torch.load('{}/model_checkpoint.pt'.format(model_dir))['model'])

    # load test data
    dataloader_test = DataLoader(
        dataset= ImageFolder(root=os.path.join(data_dir, 'test'), transform=mnist_transforms['test']),
        batch_size=64,
        shuffle=False,
        num_workers=4
    )
    print('Size test dataset: {}'.format(len(dataloader_test.dataset)))

    print('Running inference on test data')
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print('Using device: {}'.format(device))
    
    # inference
    model.eval()
    model.to(device)
    loss, correct = 0, 0
    with torch.no_grad():
        for imgs, targets in dataloader_test:
            imgs, targets = imgs.to(device), targets.to(device)
            output = model(imgs)
            loss += F.nll_loss(output, targets, reduction='sum').item() # sum up batch loss
            pred = output.argmax(dim=1, keepdim=True) # get the index of the max log-probability
            correct += pred.eq(targets.view_as(pred)).sum().item()
    loss /= len(dataloader_test.dataset)
    accuracy = correct / len(dataloader_test.dataset)
    
    print('Test set: Average loss: {:.4f}, Accuracy: {}/{} ({:.3f}%)\n'.format(
        loss, correct, len(dataloader_test.dataset),
        100. * accuracy))


def initialize_model(args):
    """Reads given lr and creates intial model"""
    
    # initialize model
    model = ClassifierMNIST()
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr_initial)
    print('Model initialization! (learning rate: {}'.format(args.lr_initial))

    # saving initial model
    model_checkpoint = {
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict()
    }
    print('Saving initial model for further processing')
    torch.save(model_checkpoint, os.path.join(args.model_dir, 'model_checkpoint.pt'))
    print('Saving initial model to checkpoints directory')
    torch.save(model_checkpoint, os.path.join(args.checkpoints_dir, '{}-checkpoint_initial.pt'.format(time.strftime("%Y%m%d-%H%M%S"))))

    # save timestamp log
    filename = os.path.join(args.logging, 'federated_exp_logging.json')
    ts_init = time.time()
    log_entry = {
            'description': 'init',
            'fed_round': args.fed_round,
            'ts': ts_init,
            'ts_date': datetime.fromtimestamp(ts_init).strftime('%Y-%b-%d-%H-%M-%S')
        }
    logs = []
    logs.append(log_entry)

    with open(filename, 'w') as file:
        json.dump(logs, file, indent=2)
    print('Saved initialization timestamp!')


def main(args):

    # clear cache (airflow dir) - Done to not carry on all checkpoints - they are saved in Minio anyways
    shutil.rmtree(args.checkpoints_dir)
    if not os.path.exists(args.checkpoints_dir):
        os.makedirs(args.checkpoints_dir)


    #### Model processing - Sequential Training ###
    if args.procedure == 'seq':
        print('#'*15, 'Sequential training - worker: {} round: {}/{}'.format(args.worker, args.fed_round, args.fed_rounds_total))
        
        # load recieved model
        print('Loading model recieved from worker: {}'.format(args.worker))
        checkpoint = torch.load('{}/model_checkpoint_from_{}.pt'.format(args.model_cache, args.worker))
        model_state_dict, optimizer_state_dict = checkpoint['model'], checkpoint['optimizer']
        
        model = ClassifierMNIST()
        model.load_state_dict(model_state_dict)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.1) # --> hard coded learning rate is overwritten in next line!
        optimizer.load_state_dict(optimizer_state_dict)

        save_checkpoint(args, model, optimizer)

    
    #### Model processing - Averaging ###
    elif args.procedure == 'avg':
        print('#'*15, 'Averaging recieved models - round {}/{}'.format(args.fed_round, args.fed_rounds_total))
        
        # get file paths of received models and save the models as backups
        model_file_list = [f'{args.model_cache}/model_checkpoint_from_{participant}.pt' for participant in args.participants]
        save_checkpoints_before_avg(args, model_file_list)
        
        # get state dicts of received models
        model_state_dicts = [torch.load(model)['model'] for model in model_file_list]

        # average models to new model
        print('Apply averaging on ({}) models: {}'.format(len(model_file_list) ,model_file_list))
        model = ClassifierMNIST()
        sd_avg = average_model_state_dicts(model_state_dicts)
        model.load_state_dict(sd_avg)

        # optimizer
        optimizer = torch.optim.SGD(model.parameters(), lr=0.1) # --> hard coded learning rate is overwritten in next line!
        optimizer.load_state_dict(
            torch.load(model_file_list[0])['optimizer']
        )

        save_checkpoint(args, model, optimizer)
    
    else:
        raise AssertionError('Procedure needs to be set either "avg" or "seq"')


if __name__ == '__main__':
    args = Arguments()
    
    if args.initialize_model:
        initialize_model(args)
    elif args.inference:
        inference(**args.__dict__)
    else:
        main(args)
