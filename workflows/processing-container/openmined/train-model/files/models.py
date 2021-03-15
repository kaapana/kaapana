import os

import torch as th
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models


# simple net for MNIST example
class SimpleNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 20, 5, 1)
        self.conv2 = nn.Conv2d(20, 50, 5, 1)
        self.fc1 = nn.Linear(4*4*50, 500)
        self.fc2 = nn.Linear(500, 10)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.max_pool2d(x, 2, 2)
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2, 2)
        x = x.view(-1, 4*4*50)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)


# pretrained ResNet18
class ResNet18(nn.Module):
    def __init__(self, num_classes=2):
        super().__init__()        
        self.num_classes = num_classes

        #self.feature_extractor = th.load('models/resnet18.pt') 
        self.feature_extractor= models.resnet18(pretrained=True) # --> container needs internet access!
        self.num_fts = self.feature_extractor.fc.in_features # 512 features

        self.feature_extractor.fc = nn.Linear(self.num_fts, 256)
        self.feature_extractor.eval()

        self.fc01 = nn.Linear(256, 128)
        self.fc02 = nn.Linear(128, self.num_classes)

    def forward(self, x):
        out = self.feature_extractor(x)
        out = F.relu(self.fc01(out))
        return self.fc02(out)


def get_model(example: str):
    '''Return requested model / architecture for example'''

    if example == 'mnist_example':
        return SimpleNet()
    elif example == 'xray_example':
        return ResNet18()
    return None


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
        return th.load(model_file_path)
    except:
        return None



