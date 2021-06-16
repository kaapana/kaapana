import os
import json

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

from torch.utils.tensorboard import SummaryWriter

from utilities import ClassifierMNIST, mnist_transforms


class Arguments():
    def __init__(self):
        '''Set args from envs given by Airflow operator'''
        
        self.host_ip = os.environ['HOST_IP']
        
        self.data_path = os.path.join(os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
        self.train_data_dir = os.path.join(self.data_path, 'train')
        self.val_data_dir = os.path.join(self.data_path, 'val')
        
        self.model_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'model')
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
        
        self.model_cache = os.path.join(os.environ['WORKFLOW_DIR'], 'cache')
        if not os.path.exists(self.model_cache):
            os.makedirs(self.model_cache)
        
        self.checkpoints_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'checkpoints')
        if not os.path.exists(self.checkpoints_dir):
            os.makedirs(self.checkpoints_dir)
        
        self.log_dir = '/data/logs'
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        self.tensorboard = '/data/tensorboard'

        self.num_workers = 4
        self.log_interval = 100
        self.batch_size = int(os.environ['BATCH_SIZE'])
        self.use_cuda = (os.environ.get('USE_CUDA', 'False') == 'True')
        self.validation = (os.environ.get('VALIDATION', 'False') == 'True')

        self.n_epochs = int(os.environ['N_EPOCHS'])
        self.fed_round = int(os.environ['FED_ROUND']) if os.environ['FED_ROUND'] != 'None' else 0
        self.epoch = (self.fed_round * self.n_epochs)


def validate(args, model, dataloader_val, epoch, device, tb_logger):
    model.eval()
    val_loss = 0
    correct = 0
    with torch.no_grad():
        for imgs, targets in dataloader_val:
            imgs, targets = imgs.to(device), targets.to(device)
            output = model(imgs)
            val_loss += F.nll_loss(output, targets, reduction='sum').item() # sum up batch loss
            pred = output.argmax(dim=1, keepdim=True) # get the index of the max log-probability
            correct += pred.eq(targets.view_as(pred)).sum().item()
    val_loss /= len(dataloader_val.dataset)
    accuracy = correct / len(dataloader_val.dataset)
    
    print('Validation set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
        val_loss, correct, len(dataloader_val.dataset),
        100. * accuracy))
    
    # tensorboad logging
    tb_logger.add_scalar("Loss_Validation_Epochs", val_loss, epoch)
    tb_logger.add_scalar("Accuracy_Validation_Epochs", accuracy, epoch)


def train(args, model, optimizer, dataloader_train, epoch, device, tb_logger):
    
    # loading logs file to append
    filename = os.path.join(args.log_dir, 'mnist_exp_loss_logging_{}.json'.format(args.host_ip))
    if args.fed_round == 0:
        loss_logs = []
    else:
        loss_logs = json.load(open(filename))
        print('Loaded loss logs from {}!'.format(filename))
    
    # start training
    model.train()
    loss_epoch = 0
    correct = 0
    for batch_idx, (imgs, targets) in enumerate(dataloader_train):
        imgs, targets = imgs.to(device), targets.to(device)
        optimizer.zero_grad()
        output = model(imgs)
        pred = output.argmax(dim=1, keepdim=True) # get the index of the max log-probability
        correct += pred.eq(targets.view_as(pred)).sum().item()
        loss = F.nll_loss(output, targets)
        loss_epoch += loss.item() # accumulating batch losses
        loss.backward()
        optimizer.step()

        # log to file
        current_step = len(loss_logs)
        log_entry = {
            'step': current_step,
            'loss': loss.item,
            'fed_round': args.fed_round,
            'epoch': args.epoch,
            'participant': args.host_ip
        }
        loss_logs.append(log_entry)
    
        # Tensorboard logging each step
        tb_logger.add_scalar("Loss_Training_Steps", loss, current_step)    
        
        # print training metrics
        if batch_idx % args.log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(imgs), len(dataloader_train.dataset),
                100. * batch_idx / len(dataloader_train), loss.item()))
    
    loss_epoch /= len(dataloader_train) # divide by number of batches
    accuracy = correct / len(dataloader_train.dataset)
    
    # save logs list to json file
    with open(filename, 'w') as file:
        json.dump(loss_logs, file, indent=2)

    # tensorboad logging
    tb_logger.add_scalar("Loss_Training_Epochs", loss_epoch, epoch)
    tb_logger.add_scalar("Accuracy_Training_Epochs", accuracy, epoch)


def main(args):

    # logging
    tb_logger = SummaryWriter(
        log_dir='{}/participant-{}'.format(args.logs_dir, args.host_ip),
        filename_suffix='-fed_round_{}'.format(args.fed_round)
    )

    # check for cuda
    device = torch.device('cuda' if args.use_cuda and torch.cuda.is_available() else 'cpu')
    print('Using device: {}'.format(device))

    # dataloader 
    dataloader_train = DataLoader(
        dataset=ImageFolder(root=args.train_data_dir, transform=mnist_transforms['train']),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers
    )
    
    dataloader_val = DataLoader(
        dataset= ImageFolder(root=args.val_data_dir, transform=mnist_transforms['val']),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers
    )

    # model & optimizer
    checkpoint = torch.load(os.path.join(args.model_dir, 'model_checkpoint.pt'))
    
    model = ClassifierMNIST()
    model.load_state_dict(checkpoint['model'])
    
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0)
    optimizer.load_state_dict(checkpoint['optimizer']) # <-- overwrites previously set default_lr

    # training
    print('Run {} local training epochs'.format(args.n_epochs))
    model.to(device)
    for epoch in range(args.epoch, args.epoch + args.n_epochs):
        train(args, model, optimizer, dataloader_train, epoch, device, tb_logger)
        
        if args.validation:
            validate(args, model, dataloader_val, epoch, device, tb_logger)
    
    tb_logger.flush()

    # save new model checkpoint (with source label)
    checkpoint = {
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict()
    }
    torch.save(checkpoint, os.path.join(args.model_cache, 'model_checkpoint_from_{}.pt'.format(args.host_ip)))


if __name__ == '__main__':
    args = Arguments()
    print(
        '########### Training on MNIST ###########',
        'Federated Round: {}'.format(args.fed_round),
        'Batch size: {}'.format(args.batch_size),
        sep='\n'
    )
    main(args)
