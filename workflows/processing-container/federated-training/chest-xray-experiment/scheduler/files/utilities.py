import os
import time

from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms, models


class ResNet18(nn.Module):
    def __init__(self, channels=3, num_classes=2, pretrained=False):
        super(ResNet18, self).__init__()
        self.channels = channels
        self.num_classes = num_classes

        self.feature_extractor = models.resnet18(pretrained=pretrained)
        num_ftrs = self.feature_extractor.fc.in_features
        self.feature_extractor.fc = nn.Linear(num_ftrs, self.num_classes)

        if pretrained:
            print('Loaded pre-trained ResNet18 state dict!')        

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
    'val': transforms.Compose([
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
        ])
}


def average_model_state_dicts(state_dicts):
    """Takes multiple state dicts to calculate their average"""
    model_sd_avg = dict()
    for key in state_dicts[0]:
        #model_sd_avg[key] = sum([state_dict[key] for state_dict in state_dicts]) / len(state_dicts)
        model_sd_avg[key] = torch.true_divide(
            sum([state_dict[key] for state_dict in state_dicts]), 
            len(state_dicts)
        ) 
    return model_sd_avg


def save_checkpoint(args, model, optimizer):
    """Saves model & optimizer as checkpoint"""
    
    model_checkpoint = {
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict()
    }
    
    print('Saving model for next next forward-pass')
    torch.save(model_checkpoint, os.path.join(args.model_dir, 'model_checkpoint.pt'))
    
    # save and keep checkpoint
    if args.procedure == 'seq':
        print('Saving a copy of the model to checkpoints directory')
        torch.save(model_checkpoint, os.path.join(args.checkpoints_dir, '{}-checkpoint_round_{}_{}.pt'.format(time.strftime("%Y%m%d-%H%M%S"), args.fed_round, args.worker)))
    else:
        torch.save(model_checkpoint, os.path.join(args.checkpoints_dir, '{}-checkpoint_round_{}.pt'.format(time.strftime("%Y%m%d-%H%M%S"), args.fed_round)))


def save_checkpoints_before_avg(args, file_path_list):
    """Saves the received models to checkpoints directory to serve as backups"""
    
    for filepath in file_path_list:
        checkpoint = torch.load(filepath)
        filename, extension = os.path.splitext(os.path.basename(filepath))

        filename_new = '{}-{}_round_{}{}'.format(
            time.strftime("%Y%m%d-%H%M%S"),
            filename,
            args.fed_round,
            extension
        )
        torch.save(checkpoint, os.path.join(args.checkpoints_dir, filename_new))