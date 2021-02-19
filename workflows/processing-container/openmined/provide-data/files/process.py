import time
import os

import syft as sy
from syft.grid.clients.data_centric_fl_client import DataCentricFLClient
import torch
import torchvision

from torchvision import transforms
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

from utils.utilities import provide_dataset_transforms

hook = sy.TorchHook(torch)

# define path
path = os.path.join(os.environ["WORKFLOW_DIR"], os.environ['OPERATOR_IN_DIR'])

# transformations
transform_dict = provide_dataset_transforms(dataset=os.environ['DATASET'])

# Image folder
dataset = ImageFolder(
    root=os.path.join(path, 'train'),
    transform=transform_dict['train'])

# data loader
n_samples = len(dataset)
print(f'Total dataset size: {n_samples}')
dataloader = DataLoader(dataset, batch_size=n_samples, shuffle=True, num_workers=0)

# get images & targets
dataiter = iter(dataloader)
images, targets = dataiter.next()

# sending data to node
node_addr = 'http://{}:{}/'.format(os.environ['NODE_HOST'],os.environ['NODE_PORT'])
node = DataCentricFLClient(hook, node_addr)

print(f'Sending data to node {node_addr}')
imgs_tag = images.tag('#X', f"#{os.environ['DATASET']}", '#dataset').describe(f"{os.environ['DATASET']} - images")
targets_tag = targets.tag('#Y', f"#{os.environ['DATASET']}", '#dataset').describe(f"{os.environ['DATASET']} - targets")
imgs_ptr, targets_ptr = imgs_tag.send(node), targets_tag.send(node)

# sleeper
minutes = int(os.environ["LIFESPAN"])
print(f'Sleeping for {minutes} min ...')
time.sleep(minutes * 60)