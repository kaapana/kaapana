import os

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models


def get_model_from_minio(model_file_name: str):
    '''Loads model from mounted minio folder - if available'''
    
    model_file_path = os.path.join('models', 'models', model_file_name)

    # check if .pt oder ptx
    if not model_file_name.lower().endswith(tuple(['.pt', '.pth'])):
        raise AssertionError (f"Model saved in minio needs to be PyTorch model (.pt or .pth) - ({model_file_name}).")
    # check if available
    if not os.path.isfile(model_file_path):
        raise AssertionError (f"No model found using given file name ({model_file_path}).")
    
    # load and return model from minio
    try:
        print(f"Loading model from minio: {model_file_path}")
        return torch.load(model_file_path)
    except:
        return None


# simple net for MNIST example
# based on PyTorch MNIST example: https://github.com/pytorch/examples/blob/master/mnist/main.py
class SimpleNet(nn.Module): 
    def __init__(self):
        super(SimpleNet, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.dropout1 = nn.Dropout(0.25)
        self.dropout2 = nn.Dropout(0.5)
        self.fc1 = nn.Linear(9216, 128)
        self.fc2 = nn.Linear(128, 10)
    
    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2)
        x = self.dropout1(x)
        x = torch.flatten(x, 1)
        x = F.relu(self.fc1(x))
        x = self.dropout2(x)
        x = self.fc2(x)
        output = F.log_softmax(x, dim=1)
        return output


# pretrained ResNet18
class ResNet18(nn.Module):
    def __init__(self, num_classes=2, pretrained=True):
        super().__init__()        
        self.num_classes = num_classes

        self.feature_extractor= models.resnet18(pretrained=pretrained)
        self.num_fts = self.feature_extractor.fc.in_features # 512 features

        self.feature_extractor.fc = nn.Linear(self.num_fts, 256)
        self.feature_extractor.eval()

        self.fc01 = nn.Linear(256, 128)
        self.fc02 = nn.Linear(128, self.num_classes)

    def forward(self, x):
        out = self.feature_extractor(x)
        out = F.relu(self.fc01(out))
        return self.fc02(out)
