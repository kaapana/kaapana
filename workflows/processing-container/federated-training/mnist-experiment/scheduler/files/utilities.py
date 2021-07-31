import os
import time

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms


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


# transforms
mnist_transforms = {
    'train': transforms.Compose([
        transforms.Grayscale(num_output_channels=1), # <-- needed since imgs are loaded with 3 channels by default
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
        ]),
    'val': transforms.Compose([
        transforms.Grayscale(num_output_channels=1), # <-- needed since imgs are loaded with 3 channels by default
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
        ]),
    'test': transforms.Compose([
        transforms.Grayscale(num_output_channels=1), # <-- needed since imgs are loaded with 3 channels by default
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
        ])
}


def average_model_state_dicts(state_dicts):
    """Takes multiple state dicts to calculate their average"""
    model_sd_avg = dict()
    for key in state_dicts[0]:
        model_sd_avg[key] = torch.true_divide(
            sum([state_dict[key] for state_dict in state_dicts]), 
            len(state_dicts)
        ) 
    return model_sd_avg


def save_checkpoint(args, model, optimizer):
    """Saves model & optimizer as checkpoint"""
    
    model_checkpoint = {
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict()
    }
    
    print('Saving model for next next forward-pass')
    torch.save(model_checkpoint, os.path.join(args.model_dir, 'model_checkpoint.pt'))
    
    # save and keep checkpoint
    if args.procedure == 'seq':
        print('Saving a copy of the model to checkpoints directory')
        torch.save(model_checkpoint, os.path.join(args.checkpoints_dir, '{}-checkpoint_round_{}_{}.pt'.format(time.strftime("%Y%m%d-%H%M%S"), args.fed_round, args.worker)))
    else:
        torch.save(model_checkpoint, os.path.join(args.checkpoints_dir, '{}-checkpoint_round_{}.pt'.format(time.strftime("%Y%m%d-%H%M%S"), args.fed_round)))


def save_checkpoints_before_avg(args, file_path_list):
    """Saves the received models to checkpoints directory to serve as backups"""
    
    for filepath in file_path_list:
        checkpoint = torch.load(filepath)
        filename, extension = os.path.splitext(os.path.basename(filepath))

        filename_new = '{}-{}_round_{}{}'.format(
            time.strftime("%Y%m%d-%H%M%S"),
            filename,
            args.fed_round,
            extension
        )
        torch.save(checkpoint, os.path.join(args.checkpoints_dir, filename_new))
