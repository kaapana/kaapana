import time
import os

import syft as sy
from syft.grid.clients.data_centric_fl_client import DataCentricFLClient
import torch
import torchvision
from torchvision import transforms

from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

hook = sy.TorchHook(torch)

# define path
path = os.path.join(os.environ["WORKFLOW_DIR"], os.environ['OPERATOR_IN_DIR'])

# transformations
transform_dict = {
    'train': transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
        ]),
    'test': transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
        ])}

# Image folder
dataset_train = ImageFolder(
    root=os.path.join(path, 'train'),
    transform=transform_dict['train'])

# data loader
n_samples = len(dataset_train)
train_dataloader = DataLoader(dataset_train,batch_size=n_samples, shuffle=True, num_workers=0)
dataiter = iter(train_dataloader)

# get images & targets
images, targets = dataiter.next()

# sending data to node
node_addr = 'http://{}:{}/'.format(os.environ['NODE_HOST'],os.environ['NODE_PORT'])
node = DataCentricFLClient(hook, node_addr)

print(f'Sending data to node {node_addr}')
imgs_tag = images.tag('#X', '#mnist', '#dataset').describe('MNIST - images')
targets_tag = targets.tag('#Y', '#mnist', '#dataset').describe('MNIST - targets')
imgs_ptr, targets_ptr = imgs_tag.send(node), targets_tag.send(node)

# sleeper
minutes = int(os.environ["LIFESPAN"])
print(f'Sleeping for {minutes} min ...')
time.sleep(minutes * 60)