import os

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

from torch.utils.tensorboard import SummaryWriter

from utilities import ResNet18, xray_transforms


class Arguments():
    def __init__(self):
        '''Set args from envs given by Airflow operator'''
        
        self.host_ip = os.environ['HOST_IP']

        self.logs_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'logs')
        
        self.data_path = os.path.join(os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
        self.train_data_dir = os.path.join(self.data_path, 'train')
        self.test_data_dir = os.path.join(self.data_path, 'test')
        
        self.model_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'model')
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
        
        self.model_cache = os.path.join(os.environ['WORKFLOW_DIR'], 'cache')
        if not os.path.exists(self.model_cache):
            os.makedirs(self.model_cache)
        
        self.num_workers = 16
        self.log_interval = 10
        self.batch_size = int(os.environ['BATCH_SIZE'])
        self.use_cuda = (os.environ.get('USE_CUDA', 'False') == 'True')
        self.local_testing = (os.environ.get('LOCAL_TESTING', 'False') == 'True')

        self.n_epochs = int(os.environ['N_EPOCHS'])
        self.fed_round = int(os.environ['FED_ROUND']) if os.environ['FED_ROUND'] != 'None' else 0
        self.epoch = (self.fed_round * self.n_epochs)


def test(model, dataloader_test, device):
    model.eval()
    test_loss = 0
    correct = 0
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


def train(model, optimizer, dataloader_train, epoch, device, tb_logger):
    model.train()
    loss_epoch = 0
    for batch_idx, (imgs, targets) in enumerate(dataloader_train):
        imgs, targets = imgs.to(device), targets.to(device)
        optimizer.zero_grad()
        output = model(imgs)
        loss = F.nll_loss(output, targets)
        loss_epoch += loss.item()
        loss.backward()
        optimizer.step()
        if batch_idx % args.log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(imgs), len(dataloader_train.dataset),
                100. * batch_idx / len(dataloader_train), loss.item()))
    
    # tensorboad logging
    tb_logger.add_scalar("Loss", loss_epoch, epoch)


def main(args):
    print('#'*10, 'Training on Chest-Xray data', '#'*10)

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
        dataset=ImageFolder(root=args.train_data_dir, transform=xray_transforms['train']),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers
    )
    
    dataloader_test = DataLoader(
        dataset= ImageFolder(root=args.test_data_dir, transform=xray_transforms['test']),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers
    )

    # model & optimizer
    checkpoint = torch.load(os.path.join(args.model_dir, 'model_checkpoint.pt'))
    
    model = ResNet18()
    model.load_state_dict(checkpoint['model'])
    
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    optimizer.load_state_dict(checkpoint['optimizer']) # <-- overwrites previously set default_lr

    # training
    print('Run {} local training epochs'.format(args.n_epochs))
    model.to(device)
    for epoch in range(args.epoch, args.epoch + args.n_epochs):
        train(model, optimizer, dataloader_train, epoch, device, tb_logger)
        if args.local_testing:
            test(model, dataloader_test, device)
    tb_logger.flush()

    # save new model checkpoint (with source label)
    checkpoint = {
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict()
    }
    torch.save(checkpoint, os.path.join(args.model_cache, 'model_checkpoint_from_{}.pt'.format(args.host_ip)))


if __name__ == '__main__':
    args = Arguments()
    main(args)