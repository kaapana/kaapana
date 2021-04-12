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
    'test': transforms.Compose([
        transforms.Grayscale(num_output_channels=1), # <-- needed since imgs are loaded with 3 channels by default
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
        ])}