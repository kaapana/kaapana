import syft as sy
from syft.grid.public_grid import PublicGridNetwork

import os
import datetime
import torch as th
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import StepLR

from utils.models import SimpleNet, get_model_from_minio
from utils.utilities import FederatedExperiment, OpenminedDataset, shutdown_data_provider

# PySyft hooking PyTorch
hook = sy.TorchHook(th)


class FedExp_MNIST(FederatedExperiment):
    """
    Exemplary experiment on the MNIST dataset
    """
    
    def __init__(self, grid_host, grid_port):
        super().__init__(grid_host, grid_port)
        
        self.exp_tag = os.getenv('EXP_TAG', '#testing')
        self.grid_addr = 'http://{}:{}'.format(self.grid_host, self.grid_port)
        self.grid = PublicGridNetwork(hook, self.grid_addr)
        
        self.epochs = int(os.getenv('EPOCHS', 1))
        self.batch_size = int(os.getenv('BATCH_SIZE', 512))
        self.lr = float(os.getenv('LEARNING_RATE', 1.0))
        self.gamma = float(os.getenv('GAMMA', 0.7))
        
        self.model = SimpleNet()
        self.dataloaders, self.workers = self._get_dataloaders()

        # load model from minio
        #self.model = get_model_from_minio(model_file_name='resnet18.pt')
        

    def run_experiment(self):
        print("\n##### RUNNING EXPERIMENT (FedExp_MNIST) #####")
        start = datetime.datetime.now()

        optimizer = optim.SGD(self.model.parameters(), lr=self.lr)
        scheduler = StepLR(optimizer, step_size=1, gamma=self.gamma)

        for epoch in range(self.epochs):
            print(f'# Epoch: {epoch}')
            self._train(epoch, optimizer)
            scheduler.step()
        
        end = datetime.datetime.now()
        print("Model training finished!")
        print("Training time: {}\n".format(end - start))


    def _train(self, epoch, optimizer):

        #iterate over the remote workers - send model to its location
        for worker in self.workers.values():
            self.model.train()
            self.model.send(worker)
            
            #iterate over batches of remote data
            dataloader = self.dataloaders[worker.id]
            for batch_idx, (imgs, labels) in enumerate(dataloader):
                optimizer.zero_grad()
                pred = self.model(imgs)
                loss = F.nll_loss(pred, labels)
                loss.backward()
                optimizer.step()
                
            #get model and loss back from remote worker
            self.model.get()
            loss = loss.get()

            print("Train Epoch: {} | With {} data ({}) | Loss: {:.6f}".format(
                epoch, str(worker.id).upper(), len(dataloader.dataset) ,loss.item()))

    
    def _get_dataloaders(self):
        '''Prepares dataloaders containing references to remote data'''

        # Get data pointers & workers
        data = self.grid.search("#X", "#dataset", "#mnist", self.exp_tag)
        assert (data), "No data found in PyGrid!"
        print("Data: {}".format(data))
        
        labels = self.grid.search("#Y", "#dataset", "#mnist", self.exp_tag)
        assert (labels), "No labels found in PyGrid!"
        print("Labels: {}".format(labels))
        
        workers = {worker : data[worker][0].location for worker in data.keys()}
        print(f'Workers: {workers}')

        # Dataloader using the pointers-datasets
        dataloaders = dict()
        for worker in workers.items():
            location = worker[0]
            dataloaders[location] = DataLoader(OpenminedDataset(data[location][0], labels[location][0]),
                                        batch_size=self.batch_size,
                                        shuffle=True,
                                        num_workers=0)
        print(f'Dataloader: {dataloaders}')
        return dataloaders, workers

