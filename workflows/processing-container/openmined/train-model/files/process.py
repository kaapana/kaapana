import os
import syft as sy
from syft.grid.public_grid import PublicGridNetwork

import torch as th
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from utils.dataset import OpenminedDataset
from utils.models import get_model

# hooking PyTorch
hook = sy.TorchHook(th)

# set parameter
MODEL = str(os.environ['MODEL'])
N_EPOCS = int(os.environ['EPOCHS'])
BATCH_SIZE = int(os.environ['BATCH_SIZE'])
LEARNING_RATE = float(os.environ['LEARNING_RATE'])

SAVE_MODEL = True
SAVE_MODEL_PATH = '../models'

# check gpu support
device = th.device('cuda:0' if th.cuda.is_available() else 'cpu')
print(f'Using device: {device}')

# create model
model = get_model(architecture=MODEL)
model.to(device)
optimizer = optim.SGD(model.parameters(), lr=LEARNING_RATE)
criterion = nn.CrossEntropyLoss()

# Openmined Grid
grid_addr = 'http://' + os.environ['GRID_HOST'] + ':' + os.environ['GRID_PORT']
grid = PublicGridNetwork(hook, grid_addr)

# Get data references
data = grid.search("#X", f"#{os.environ['DATASET']}", "#dataset")
print(f"Data: {data}")
labels = grid.search("#Y", f"#{os.environ['DATASET']}", "#dataset")
print(f"Labels: {labels}")

# Get Workers and their locations
workers = {worker : data[worker][0].location for worker in data.keys()}
print(f'Workers: {workers}')

# raise exception if no data/labels available
assert (workers), "No nodes/workers registered to PyGrid."
assert (data), "No data found in PyGrid."
assert (labels), "No labels found in PyGrid."

# Dataloader using the pointers-datasets
dataloaders = dict()
for worker in workers.items():
    location = worker[0]
    dataloaders[location] = DataLoader(OpenminedDataset(data[location][0],labels[location][0]),
                                   batch_size=BATCH_SIZE,
                                   shuffle=True,
                                   num_workers=0)
print(f'Dataloader: {dataloaders}')

def epoch_total_size(data):
    total = 0
    for elem in data:
        total += data[elem][0].shape[0]
#         for i in range(len(data[elem])):
#             total += data[elem][i].shape[0]
    return total


# Training on all nodes
def train(epoch):
    current_epoch_size = 0
    epoch_total = epoch_total_size(data)
    
    ''' iterate over the remote workers - send model to its location '''
    for worker in workers.values():
        model.train()
        model.send(worker)
        current_epoch_size += len(data[worker.id][0])
    
        ''' iterate over batches of remote data '''
        for batch_idx, (imgs, labels) in enumerate(dataloaders[worker.id]):

            ''' forward step '''
            pred = model(imgs)

            ''' compute loss, backprob, update parameter '''
            loss = criterion(pred, labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
        ''' get model and loss back '''
        model.get()
        loss = loss.get()

        print('Train Epoch: {} | With {} data |: [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                  epoch, str(worker.id).upper(), current_epoch_size, epoch_total,
                        100. *  current_epoch_size / epoch_total, loss.item()))

# Run training
print('\n### RUN TRAINING ###')

for epoch in range(N_EPOCS):
    print(f'# Epoch: {epoch}')
    train(epoch)