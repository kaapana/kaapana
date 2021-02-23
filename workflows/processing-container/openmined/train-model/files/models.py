import torch as th
import torch.nn as nn
import torch.nn.functional as F


# simple net for MNIST example
class SimpleNet(nn.Module):
    def __init__(self):
        super(SimpleNet, self).__init__()
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
    def __init__(self, channels=3):
        super().__init__()
        self.channels = channels
        self.num_classes = 2

        # pretrained resnet "whereas all of the other models expect (224,224)"
        # https://pytorch.org/tutorials/beginner/finetuning_torchvision_models_tutorial.html
        self.feature_extractor = th.load('../models/resnet18.pt')

        self.feat_size_in = self.feature_extractor.fc.in_features
        self.feat_size_out = self.feature_extractor.fc.out_features
        self.feature_extractor.fc = nn.Linear(512, 256)
        self.feature_extractor.eval()

        self.fc01 = nn.Linear(256, 128)
        self.fc02 = nn.Linear(128, self.num_classes)

    def forward(self, x):
        out = self.feature_extractor(x)
        out = F.relu(self.fc01(out))
        return self.fc02(out)


def get_model(architecture: str):
    '''Return requested model / architecture'''

    if architecture == 'mnist':
        print(architecture)
        return SimpleNet()
    elif architecture == 'resnet18':
        print(architecture)
        return ResNet18()
    return None