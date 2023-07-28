#!/usr/bin/env python3
import copy
import os
import random
import logging
import secrets
from enum import Enum
from pathlib import Path

import monai
import numpy as np
import torch
import torchvision.models as models
from batchgenerators.dataloading.multi_threaded_augmenter import MultiThreadedAugmenter
from batchgenerators.transforms.abstract_transforms import Compose
from batchgenerators.transforms.color_transforms import (
    BrightnessMultiplicativeTransform,
    GammaTransform,
)
from batchgenerators.transforms.noise_transforms import (
    GaussianNoiseTransform,
    GaussianBlurTransform,
)
from batchgenerators.transforms.sample_normalization_transforms import (
    ZeroMeanUnitVarianceTransform,
)
from batchgenerators.transforms.spatial_transforms import (
    SpatialTransform_2,
    MirrorTransform,
    Rot90Transform,
)
from torch import nn
from torch.utils.tensorboard import SummaryWriter
from torchmetrics import F1Score

import classification_config as config
import resnet as resnet
from batchgenerators_dataloader import FolderFilenameStructuredClassificationDataset

# Create a custom logger
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)

c_format = logging.Formatter('%(levelname)s - %(message)s')
c_handler.setFormatter(c_format)

# Add handlers to the logger
logger.addHandler(c_handler)

f1_score = F1Score(task="binary", num_classes=2)

steps_of_val = []
all_f1 = []
all_vloss = []
all_lr = []

all_steps = []
all_tloss = []
epochs_steps = {}
model_best = 0
num_classes = 1


class ModelChoices(Enum):
    MONAI_RESNET = "monai_resnet"
    MONAI_EFFICIENTNET_B0 = "monai_effnet_b0"
    MONAI_EFFICIENTNET_B1 = "monai_effnet_b1"
    MONAI_EFFICIENTNET_B2 = "monai_effnet_b2"
    MONAI_EFFICIENTNET_B3 = "monai_effnet_b3"
    MOANI_DENSENET = "monai_densenet"
    TV_RESNET = "video_resnet"
    SMPL_RESNET_18 = "smpl_resnet_18"
    SMPL_RESNET_50 = "smpl_resnet_50"
    SMPL_RESNET_101 = "smpl_resnet_101"
    SMPL_RESNET_152 = "smpl_resnet_152"
    SMPL_RESNET_200 = "smpl_resnet_200"


def get_model(model_name):
    if model_name == "monai_densenet":
        chosen_model = monai.networks.nets.DenseNet121(
            spatial_dims=3, in_channels=1, out_channels=1
        )
        chosen_model.features[0] = nn.Conv3d(
            config.NUM_INPUT_CHANNELS,
            64,
            kernel_size=(3, 7, 7),
            stride=(1, 2, 2),
            padding=(3, 3, 3),
            bias=False,
        )

    elif model_name == "monai_effnet_b0":
        chosen_model = monai.networks.nets.EfficientNetBN(
            "efficientnet-b0",
            pretrained=True,
            spatial_dims=3,
            in_channels=1,
            num_classes=1,
        )
        chosen_model._conv_stem = nn.Conv3d(
            config.NUM_INPUT_CHANNELS,
            32,
            kernel_size=(3, 7, 7),
            stride=(1, 2, 2),
            padding=(3, 3, 3),
            bias=False,
        )
        chosen_model._fc = nn.Linear(1280, num_classes, bias=True)

    elif model_name == "monai_effnet_b1":
        chosen_model = monai.networks.nets.EfficientNetBN(
            "efficientnet-b1",
            pretrained=True,
            spatial_dims=3,
            in_channels=1,
            num_classes=1,
        )
        chosen_model._conv_stem = nn.Conv3d(
            config.NUM_INPUT_CHANNELS,
            32,
            kernel_size=(3, 7, 7),
            stride=(1, 2, 2),
            padding=(3, 3, 3),
            bias=False,
        )
        chosen_model._fc = nn.Linear(1280, num_classes, bias=True)

    elif model_name == "monai_effnet_b2":
        chosen_model = monai.networks.nets.EfficientNetBN(
            "efficientnet-b2",
            pretrained=True,
            spatial_dims=3,
            in_channels=1,
            num_classes=1,
        )
        chosen_model._conv_stem = nn.Conv3d(
            config.NUM_INPUT_CHANNELS,
            32,
            kernel_size=(3, 7, 7),
            stride=(1, 2, 2),
            padding=(3, 3, 3),
            bias=False,
        )
        chosen_model._fc = nn.Linear(1408, num_classes, bias=True)

    elif model_name == "monai_effnet_b3":
        chosen_model = monai.networks.nets.EfficientNetBN(
            "efficientnet-b3",
            pretrained=True,
            spatial_dims=3,
            in_channels=1,
            num_classes=1,
        )
        chosen_model._conv_stem = nn.Conv3d(
            config.NUM_INPUT_CHANNELS,
            40,
            kernel_size=(3, 7, 7),
            stride=(1, 2, 2),
            padding=(3, 3, 3),
            bias=False,
        )

    elif model_name == "monai_resnet":
        chosen_model = monai.networks.nets.resnet18(
            pretrained=False, spatial_dims=3, no_max_pool=True
        )

        chosen_model.conv1 = nn.Conv3d(
            config.NUM_INPUT_CHANNELS,
            64,
            kernel_size=(3, 7, 7),
            stride=(1, 2, 2),
            padding=(1, 3, 3),
            bias=False,
        )
        chosen_model.fc = nn.Linear(512, num_classes, bias=True)
    elif model_name == "video_resnet":
        chosen_model = models.video.r3d_18(pretrained=True)
        chosen_model.fc = nn.Linear(512, num_classes, bias=True)
        chosen_model.stem[0] = nn.Conv3d(
            config.NUM_INPUT_CHANNELS,
            64,
            kernel_size=(3, 7, 7),
            stride=(1, 2, 2),
            padding=(1, 3, 3),
            bias=False,
        )
    elif model_name == "smpl_resnet_18":
        chosen_model = resnet.generate_model(
            model_depth=18,
            n_classes=num_classes,
            n_input_channels=config.NUM_INPUT_CHANNELS,
            shortcut_type="B",
            conv1_t_size=7,
            conv1_t_stride=3,
            no_max_pool=True,
            widen_factor=1.0,
        )
        chosen_model.conv1 = nn.Conv3d(
            config.NUM_INPUT_CHANNELS,
            64,
            kernel_size=(3, 7, 7),
            stride=(1, 2, 2),
            padding=(1, 3, 3),
            bias=False,
        )
        chosen_model.fc = nn.Linear(512, num_classes, bias=True)
    elif model_name == "smpl_resnet_50":
        chosen_model = resnet.generate_model(
            model_depth=50,
            n_classes=num_classes,
            n_input_channels=config.NUM_INPUT_CHANNELS,
            shortcut_type="B",
            conv1_t_size=7,
            conv1_t_stride=3,
            no_max_pool=True,
            widen_factor=1.0,
        )
        chosen_model.conv1 = nn.Conv3d(
            config.NUM_INPUT_CHANNELS,
            64,
            kernel_size=(3, 7, 7),
            stride=(1, 2, 2),
            padding=(1, 3, 3),
            bias=False,
        )
        chosen_model.fc = nn.Linear(2048, num_classes, bias=True)

    elif model_name == "smpl_resnet_101":
        chosen_model = resnet.generate_model(
            model_depth=101,
            n_classes=num_classes,
            n_input_channels=config.NUM_INPUT_CHANNELS,
            shortcut_type="B",
            conv1_t_size=7,
            conv1_t_stride=3,
            no_max_pool=True,
            widen_factor=1.0,
        )
        chosen_model.conv1 = nn.Conv3d(
            config.NUM_INPUT_CHANNELS,
            64,
            kernel_size=(3, 7, 7),
            stride=(1, 2, 2),
            padding=(1, 3, 3),
            bias=False,
        )
        chosen_model.fc = nn.Linear(2048, num_classes, bias=True)
    elif model_name == "smpl_resnet_152":
        chosen_model = resnet.generate_model(
            model_depth=152,
            n_classes=num_classes,
            n_input_channels=config.NUM_INPUT_CHANNELS,
            shortcut_type="B",
            conv1_t_size=7,
            conv1_t_stride=3,
            no_max_pool=True,
            widen_factor=1.0,
        )
        chosen_model.conv1 = nn.Conv3d(
            config.NUM_INPUT_CHANNELS,
            64,
            kernel_size=(3, 7, 7),
            stride=(1, 2, 2),
            padding=(1, 3, 3),
            bias=False,
        )
        chosen_model.fc = nn.Linear(2048, num_classes, bias=True)
    elif model_name == "smpl_resnet_200":
        chosen_model = resnet.generate_model(
            model_depth=200,
            n_classes=num_classes,
            n_input_channels=config.NUM_INPUT_CHANNELS,
            shortcut_type="B",
            conv1_t_size=7,
            conv1_t_stride=3,
            no_max_pool=True,
            widen_factor=1.0,
        )
        chosen_model.conv1 = nn.Conv3d(
            config.NUM_INPUT_CHANNELS,
            64,
            kernel_size=(3, 7, 7),
            stride=(1, 2, 2),
            padding=(1, 3, 3),
            bias=False,
        )
        chosen_model.fc = nn.Linear(2048, num_classes, bias=True)
    else:
        raise NotImplementedError("whoops")

    return chosen_model


def save_checkpoint(model, optimizer, filename="my_checkpoint.pth.tar"):
    print("=> Saving checkpoint")
    checkpoint = {
        "state_dict": model.state_dict(),
        "optimizer": optimizer.state_dict(),
    }
    torch.save(checkpoint, filename)


def load_checkpoint(checkpoint_file, model, optimizer, lr):
    print("=> Loading checkpoint")
    checkpoint = torch.load(checkpoint_file, map_location=config.DEVICE)
    model.load_state_dict(checkpoint["state_dict"], strict=False)
    optimizer.load_state_dict(checkpoint["optimizer"])

    # If we don't do this then it will just have learning rate of old checkpoint
    # and it will lead to many hours of debugging \:
    for param_group in optimizer.param_groups:
        param_group["lr"] = lr


def get_train_transform(patch_size):
    # we now create a list of transforms. These are not necessarily the best transforms to use for BraTS, this is just
    # to showcase some things
    tr_transforms = []

    # the first thing we want to run is the SpatialTransform. It reduces the size of our data to patch_size and thus
    # also reduces the computational cost of all subsequent operations. All subsequent operations do not modify the
    # shape and do not transform spatially, so no border artifacts will be introduced
    # Here we use the new SpatialTransform_2 which uses a new way of parameterizing elastic_deform
    # We use all spatial transformations with a probability of 0.2 per sample. This means that 1 - (1 - 0.1) ** 3 = 27%
    # of samples will be augmented, the rest will just be cropped

    tr_transforms.append(ZeroMeanUnitVarianceTransform())

    tr_transforms.append(
        Compose(
            [
                SpatialTransform_2(
                    patch_size,
                    [i // 2 for i in patch_size],
                    do_elastic_deform=True,
                    deformation_scale=(0, 0.25),
                    do_rotation=True,
                    angle_x=(-15 / 360.0 * 2 * np.pi, 15 / 360.0 * 2 * np.pi),
                    angle_y=(-15 / 360.0 * 2 * np.pi, 15 / 360.0 * 2 * np.pi),
                    angle_z=(-15 / 360.0 * 2 * np.pi, 15 / 360.0 * 2 * np.pi),
                    do_scale=True,
                    scale=(0.75, 1.25),
                    border_mode_data="constant",
                    border_cval_data=0,
                    border_mode_seg="constant",
                    border_cval_seg=0,
                    order_seg=1,
                    order_data=3,
                    random_crop=False,  # Make sure we don't crop out the true positive metastasis
                    p_el_per_sample=0.1,
                    p_rot_per_sample=0.1,
                    p_scale_per_sample=0.1,
                ),
            ]
        )
    )

    # now we mirror along all axes
    tr_transforms.append(MirrorTransform(axes=(0, 1, 2)))

    # brightness transform for 15% of samples
    tr_transforms.append(
        BrightnessMultiplicativeTransform(
            (0.7, 1.5), per_channel=True, p_per_sample=0.15
        )
    )

    # gamma transform. This is a nonlinear transformation of intensity values
    # (https://en.wikipedia.org/wiki/Gamma_correction)
    tr_transforms.append(
        GammaTransform(
            gamma_range=(0.5, 2),
            invert_image=False,
            per_channel=True,
            p_per_sample=0.15,
        )
    )
    # we can also invert the image, apply the transform and then invert back
    tr_transforms.append(
        GammaTransform(
            gamma_range=(0.5, 2), invert_image=True, per_channel=True, p_per_sample=0.15
        )
    )

    # Gaussian Noise
    tr_transforms.append(
        GaussianNoiseTransform(noise_variance=(0, 0.05), p_per_sample=0.15)
    )

    # blurring. Some BraTS cases have very blurry modalities. This can simulate more patients with this problem and
    # thus make the model more robust to it
    tr_transforms.append(
        GaussianBlurTransform(
            blur_sigma=(0.5, 1.5),
            different_sigma_per_channel=True,
            p_per_channel=0.5,
            p_per_sample=0.15,
        )
    )

    # now we compose these transforms together
    tr_transforms = Compose(tr_transforms)

    return tr_transforms


def get_split():
    random.seed(config.FOLD)

    all_samples = os.listdir(config.TRAIN_DIR)

    if len(all_samples) == 0:
        logger.error('No images in path: %s' % config.TRAIN_DIR)
        exit()

    percentage_val_samples = 15
    # 15% val. data

    num_val_samples = int(len(all_samples) / 100 * percentage_val_samples)
    val_samples = random.sample(all_samples, num_val_samples)

    train_samples = list(filter(lambda sample: sample not in val_samples, all_samples))

    return train_samples, val_samples


step = 0


def train_fn(model, criterion, mt_train, optimizer, scheduler, epoch):
    # loop = tqdm(mt_train, total=len(mt_train.data_loader.indices), leave=True)
    # loop.set_description("Training Epoch Nr.: " + str(epoch))
    # random.seed(epoch)

    global step
    losses_batches = []
    for batch_idx, batch in enumerate(mt_train):
        x = torch.from_numpy(batch["data"]).to(config.DEVICE)
        y = torch.from_numpy(batch["class"]).to(config.DEVICE)

        # img_grid = torchvision.utils.make_grid(x[:, :, 8, :, :])
        # writer.add_image("batchgenerators", img_grid)

        with torch.cuda.amp.autocast():
            # zero the parameter gradients
            optimizer.zero_grad()

            # forward + backward + optimize
            outputs = model(x)
            loss = criterion(outputs.type(torch.float32), y.type(torch.float32))
            loss.backward()
            optimizer.step()
            detached_loss = loss.detach().cpu().numpy()
            losses_batches.append(detached_loss)
        step = step + 1
        all_steps.append(step)
        all_tloss.append(detached_loss)
    if epoch > config.SCHEDULER_ENTRY:
        scheduler.step()

    return np.mean(losses_batches)


def evaluate(model, epoch, mt_val, train_loss):
    model.eval()
    all_outputs = torch.Tensor()
    all_y = torch.Tensor()
    corrects = []
    losses_batches = []
    for batch_idx, batch in enumerate(mt_val):
        x = torch.from_numpy(batch["data"]).to(config.DEVICE)
        y = torch.from_numpy(batch["class"]).to(config.DEVICE)

        with torch.no_grad():
            outputs = model(x)
            loss = criterion(outputs.type(torch.float32), y.type(torch.float32))

            corrects.append(
                torch.sum(torch.round(torch.sigmoid(outputs)) == y)
                    .detach()
                    .to("cpu")
                    .numpy()
                    .min()
            )
            all_outputs = torch.cat([all_outputs, outputs.detach().to("cpu")])
            all_y = torch.cat([all_y, y.detach().to("cpu")])
            losses_batches.append(loss.item())

    f_1 = f1_score(
        torch.round(torch.sigmoid(all_y)).type(torch.int),
        torch.round(torch.sigmoid(all_outputs)).type(torch.int),
    )

    steps_of_val.append(step)
    all_vloss.append(np.mean(losses_batches))
    all_f1.append(f_1)
    all_lr.append(optimizer.param_groups[0]["lr"])

    model.train()

    return np.mean(losses_batches), all_y.shape[0] / np.sum(corrects), f_1


def set_task():
    config.TASK = sorted(os.listdir(Path(config.PATH_TO_TASKS)))[-1]
    logger.debug('Task set to: %s' % config.TASK)


if __name__ == "__main__":

    logger.debug('Main of trainer_v2 started')
    logger.debug('Set config values')

    logger.debug('Set task from minio if is not set')

    config.TASK = secrets.token_hex(16)

    logger.debug('Train dir set to: %s' % config.TRAIN_DIR)

    config.RESULTS_DIR = Path(config.PATH_TO_RESULTS, config.TASK)
    logger.debug('Results dir set to: %s' % config.RESULTS_DIR)

    os.makedirs(config.RESULTS_DIR, exist_ok=True)

    # set patch size

    config.PATCH_SIZE = np.load(os.path.join(config.TRAIN_DIR, "classification_001.npy")).shape
    logger.debug('Patchsize set to: (%s)', ",".join(str(i) for i in config.PATCH_SIZE))
    # choose model based on config

    model_name = ModelChoices(config.MODEL)

    # set and create checkpoint path

    config.CHECKPOINT_PATH = os.path.join(
        config.RESULTS_DIR, str(model_name.value)
    )

    logger.debug('Create directories for results')

    os.makedirs(config.CHECKPOINT_PATH, exist_ok=True)
    os.makedirs(
        os.path.join(config.CHECKPOINT_PATH, "fold_%d" % config.FOLD), exist_ok=True
    )

    logger.debug('Directories created: %s' % config.CHECKPOINT_PATH)

    # load model

    model = get_model(model_name.value)

    logger.debug('Get model: %s' % str(model_name.value))

    model = model.cuda()

    logger.debug('Load model on gpu')

    model.train()

    logger.debug('Get train/val split and load batchgenerators')

    train_samples, val_samples = get_split()

    dl_train = FolderFilenameStructuredClassificationDataset(
        train_samples,
        config.BATCH_SIZE,
        config.PATCH_SIZE,
        config.NUM_WORKERS,
        seed_for_shuffle=config.FOLD,
        return_incomplete=False,
        shuffle=True,
    )

    transform = get_train_transform(config.PATCH_SIZE)

    mt_train = MultiThreadedAugmenter(
        data_loader=dl_train,
        transform=transform,
        num_processes=config.NUM_WORKERS,
        num_cached_per_queue=4,
        pin_memory=True,
    )

    dl_val = FolderFilenameStructuredClassificationDataset(
        val_samples,
        config.BATCH_SIZE,
        config.PATCH_SIZE,
        config.NUM_WORKERS,
        return_incomplete=False,
        shuffle=False,
    )

    mt_val = MultiThreadedAugmenter(
        data_loader=dl_val,
        transform=Compose([ZeroMeanUnitVarianceTransform()]),
        num_processes=config.NUM_WORKERS,
        num_cached_per_queue=4,
        pin_memory=True,
    )

    # Hyperparameters

    logger.debug('Set hyperparameters')

    criterion = torch.nn.BCEWithLogitsLoss()
    optimizer = torch.optim.SGD(
        model.parameters(), lr=2e-4, momentum=0.9, weight_decay=5e-4
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=config.NUM_EPOCHS - config.SCHEDULER_ENTRY, eta_min=1e-10
    )
    scaler = torch.cuda.amp.GradScaler()

    # Init Tensorboard

    logger.debug('Init Tensorboard')

    writer = SummaryWriter(
        os.path.join(
            config.CHECKPOINT_PATH,
            "fold_%d" % config.FOLD,
            "track_stats",
        )
    )

    val_acc_history = []
    best_model_wts = copy.deepcopy(model.state_dict())
    best_f1 = 0

    # Train loop

    logger.debug('Train loop')

    for epoch in range(0, config.NUM_EPOCHS):

        logger.debug('Current epoch: %s' % str(epoch))

        train_loss = train_fn(model, criterion, mt_train, optimizer, scheduler, epoch)

        logger.debug('Train Loss: %s' % str(train_loss))

        val_loss, corrects, f1 = evaluate(model, epoch, mt_val, train_loss)

        logger.debug('Val Loss: %s' % str(val_loss))

        writer.add_scalar("train_loss", train_loss, global_step=epoch)
        writer.add_scalar("val_loss", val_loss, global_step=epoch)
        writer.add_scalar("val_acc", corrects, global_step=epoch)
        writer.add_scalar(
            "learning_rate", optimizer.param_groups[0]["lr"], global_step=epoch
        )

        if f1 > best_f1 and len(all_steps) > config.SAVE_MODEL_START_STEP:
            best_f1 = f1
            model_best = epoch
            best_model_wts = copy.deepcopy(model.state_dict())

            logger.debug('Save checkpoint')

            save_checkpoint(
                model,
                optimizer,
                os.path.join(
                    config.CHECKPOINT_PATH,
                    "fold_%d" % config.FOLD,
                    "model_best.pth.tar",
                ),
            )

    logger.debug('Finished Training')

    save_checkpoint(
        model,
        optimizer,
        os.path.join(
            config.CHECKPOINT_PATH, "fold_%d" % config.FOLD, "model_end.pth.tar"
        ),
    )
    model.load_state_dict(best_model_wts)
