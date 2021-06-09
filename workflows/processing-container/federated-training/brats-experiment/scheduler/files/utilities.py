import os
import time
import numpy as np

from monai.networks.nets import UNet

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

import torch


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


def update_model_and_optimizer(args, model_state_dict, optimizer_state_dict):
    """loads model and optimizer - not really necessary, but here the optimizer is reset (more to come maybe)"""
    model = UNet(
        dimensions=3,
        in_channels=4,
        out_channels=3,
        channels=(16, 32, 64, 128, 256),
        strides=(2, 2, 2, 2),
        num_res_units=2,
    )
    model.load_state_dict(model_state_dict)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=1e-4,
        weight_decay=1e-5,
        amsgrad=True
    ) # --> hard coded learning rate and weight decay is overwritten in next line!
    optimizer.load_state_dict(optimizer_state_dict)
    return model, optimizer
