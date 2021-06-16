import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms


class ClassifierMNIST(nn.Module):
    def __init__(self):
        super(ClassifierMNIST, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.dropout1 = nn.Dropout(0.25)
        self.dropout2 = nn.Dropout(0.5)
        self.fc1 = nn.Linear(9216, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.conv1(x)
        x = F.relu(x)
        x = self.conv2(x)
        x = F.relu(x)
        x = F.max_pool2d(x, 2)
        x = self.dropout1(x)
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout2(x)
        x = self.fc2(x)
        output = F.log_softmax(x, dim=1)
        return output


# transforms
mnist_transforms = {
    'train': transforms.Compose([
        transforms.Grayscale(num_output_channels=1), # <-- needed since imgs are loaded with 3 channels by default
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
        ]),
    'val': transforms.Compose([
        transforms.Grayscale(num_output_channels=1), # <-- needed since imgs are loaded with 3 channels by default
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
        ]),
    'test': transforms.Compose([
        transforms.Grayscale(num_output_channels=1), # <-- needed since imgs are loaded with 3 channels by default
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
        ])
}