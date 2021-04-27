from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms, models


class ResNet18(nn.Module):
    def __init__(self, channels=3, num_classes=2):
        super(ResNet18, self).__init__()
        self.channels = channels
        self.num_classes = num_classes

        self.feature_extractor = models.resnet18(pretrained=False)
        num_ftrs = self.feature_extractor.fc.in_features
        self.feature_extractor.fc = nn.Linear(num_ftrs, self.num_classes)

    def forward(self, x):
        x = self.feature_extractor(x)
        return F.log_softmax(x, dim=1)


# transforms
xray_transforms = {
    'train': transforms.Compose([
        transforms.Resize((256, 256), interpolation=Image.NEAREST),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))  # ImageNet values
        ]),
    'test': transforms.Compose([
        transforms.Resize((256, 256), interpolation=Image.NEAREST),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))  # ImageNet values
        ]),
}
