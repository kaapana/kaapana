import os
import numpy as np

import torch

from monai.networks.nets import UNet
from monai.data import DataLoader
#from monai.apps import DecathlonDataset

from monai.transforms import (
    AsChannelFirstd,
    CenterSpatialCropd,
    Compose,
    LoadImaged,
    MapTransform,
    NormalizeIntensityd,
    Orientationd,
    RandFlipd,
    RandScaleIntensityd,
    RandShiftIntensityd,
    RandSpatialCropd,
    Spacingd,
    ToTensord,
)

# cusomized MONAI DecathlonDataset
from dataset import DecathlonDataset


class ConvertToMultiChannelBasedOnBratsClassesd(MapTransform):
    """
    Convert labels to multi channels based on brats classes:
    label 1 is the peritumoral edema
    label 2 is the GD-enhancing tumor
    label 3 is the necrotic and non-enhancing tumor core
    The possible classes are TC (Tumor core), WT (Whole tumor)
    and ET (Enhancing tumor).

    """

    def __call__(self, data):
        d = dict(data)
        for key in self.keys:
            result = []
            # merge label 2 and label 3 to construct TC
            result.append(np.logical_or(d[key] == 2, d[key] == 3))
            # merge labels 1, 2 and 3 to construct WT
            result.append(
                np.logical_or(
                    np.logical_or(d[key] == 2, d[key] == 3), d[key] == 1
                )
            )
            # label 2 is ET
            result.append(d[key] == 2)
            d[key] = np.stack(result, axis=0).astype(np.float32)
        return d


### APPLIED TRANSOFRMATIONS ###
TRAIN_TRANSFORM = Compose(
    [
        # load 4 Nifti images and stack them together
        LoadImaged(keys=["image", "label"]),
        AsChannelFirstd(keys="image"),
        ConvertToMultiChannelBasedOnBratsClassesd(keys="label"),
        Spacingd(
            keys=["image", "label"],
            pixdim=(1.5, 1.5, 2.0),
            mode=("bilinear", "nearest"),
        ),
        Orientationd(keys=["image", "label"], axcodes="RAS"),
        RandSpatialCropd(
            keys=["image", "label"], roi_size=[128, 128, 64], random_size=False
        ),
        RandFlipd(keys=["image", "label"], prob=0.5, spatial_axis=0),
        NormalizeIntensityd(keys="image", nonzero=True, channel_wise=True),
        RandScaleIntensityd(keys="image", factors=0.1, prob=0.5),
        RandShiftIntensityd(keys="image", offsets=0.1, prob=0.5),
        ToTensord(keys=["image", "label"]),
    ]
)
VAL_TRANSFORM = Compose(
    [
        LoadImaged(keys=["image", "label"]),
        AsChannelFirstd(keys="image"),
        ConvertToMultiChannelBasedOnBratsClassesd(keys="label"),
        Spacingd(
            keys=["image", "label"],
            pixdim=(1.5, 1.5, 2.0),
            mode=("bilinear", "nearest"),
        ),
        Orientationd(keys=["image", "label"], axcodes="RAS"),
        CenterSpatialCropd(keys=["image", "label"], roi_size=[128, 128, 64]),
        NormalizeIntensityd(keys="image", nonzero=True, channel_wise=True),
        ToTensord(keys=["image", "label"]),
    ]
)
### APPLIED TRANSOFRMATIONS ###


def prepare_data_loader(args):
    print('Start preparing data loaders...')
    
    train_dataset = DecathlonDataset(
        root_dir=args.root_dir,
        task="Task01_BrainTumour",
        transform=TRAIN_TRANSFORM,
        section="training",
        download=False,
        num_workers=4,
        cache_num=32,
    )
    print("Size dataset training:", len(train_dataset))
    train_loader = DataLoader(train_dataset, batch_size=2, shuffle=True, num_workers=4)

    val_dataset = DecathlonDataset(
        root_dir=args.root_dir,
        task="Task01_BrainTumour",
        transform=VAL_TRANSFORM,
        section="validation",
        download=False,
        num_workers=4,
    )
    print("Size dataset validation:", len(val_dataset))
    val_loader = DataLoader(val_dataset, batch_size=2, shuffle=False, num_workers=4)
    print('Finished preparing data loaders...')

    return train_loader, val_loader


def prepare_model_and_optimizer(args, device):
    """Loads model/optimizer received from scheduler
    
    IMPORTANT:
    Send model to device before initializing optimizer (and loading state dict).
    Otherwise, the training will fail due to cpu/gpu tensors.
    See: https://discuss.pytorch.org/t/effect-of-calling-model-cuda-after-constructing-an-optimizer/15165/5
    See: https://pytorch.org/tutorials/beginner/saving_loading_models.html#saving-loading-model-across-devices
    --> not 100% sure whats happening exactly!
    """

    checkpoint = torch.load(os.path.join(args.model_dir, 'model_checkpoint.pt'), map_location="cuda:0")

    model = UNet(
        dimensions=3,
        in_channels=4,
        out_channels=3,
        channels=(16, 32, 64, 128, 256),
        strides=(2, 2, 2, 2),
        num_res_units=2,
    )
    model.load_state_dict(checkpoint['model'])
    
    # send model to GPU
    model.to(device)

    optimizer = torch.optim.Adam(
        model.parameters(), args.lr, weight_decay=args.weight_decay, amsgrad=True
    ) # <-- values could be overwritten in next step (here to optimizer state is RESET)
    # optimizer.load_state_dict(checkpoint['optimizer'])
    print("Optimizer:", optimizer)

    return model, optimizer


def save_model(args, model, optimizer, final=False):
    """Saves model & optimizer as checkpoint either to send back """
    
    model_checkpoint = {
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict()
    }
    if final:
        file_path = os.path.join(args.model_cache, 'model_checkpoint_from_{}.pt'.format(args.host_ip))
    else:
        file_path = os.path.join(args.checkpoints_dir, 'model_checkpoint_from_{}_round_{}.pt'.format(args.host_ip, args.fed_round))
    torch.save(model_checkpoint, file_path)


def check_for_cuda():
    if torch.cuda.is_available():
        device = torch.device('cuda:0')
        print('Using device: {}'.format(device))
    else:
        raise Exception ('Cuda is not available!')
    return device

