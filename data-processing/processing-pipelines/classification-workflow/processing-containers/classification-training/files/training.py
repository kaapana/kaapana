#!/usr/bin/env python3
import copy
import os
import random
import logging
import secrets
from enum import Enum
from pathlib import Path
import ast

import monai
import numpy as np
import torch
import torchvision.models as models

from torch import nn
from torch.utils.tensorboard import SummaryWriter
from torchmetrics import F1Score

import classification_config as config
import resnet as resnet
from batchgenerators_dataloader import ClassificationDataset
from batchgenerators.dataloading.multi_threaded_augmenter import MultiThreadedAugmenter
from batchgenerators.transforms.abstract_transforms import Compose
from batchgenerators.transforms.sample_normalization_transforms import (
    ZeroMeanUnitVarianceTransform,
)
from opensearch_helper import OpenSearchHelper

# Create a custom logger
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)

c_format = logging.Formatter('%(levelname)s - %(message)s')
c_handler.setFormatter(c_format)

# Add handlers to the logger
logger.addHandler(c_handler)

TAG_TO_CLASS_MAPPING = ast.literal_eval(os.environ['TAG_TO_CLASS_MAPPING_JSON'])

if len(TAG_TO_CLASS_MAPPING) < 2:
    raise ValueError(f"Some issue with the class mapping json: {TAG_TO_CLASS_MAPPING}")
elif len(TAG_TO_CLASS_MAPPING) == 2:
    f1_score = F1Score(task="binary", num_classes=2)
else:
    f1_score = F1Score(task="multiclass", num_classes=len(TAG_TO_CLASS_MAPPING))

steps_of_val = []
all_f1 = []
all_vloss = []
all_lr = []

all_steps = []
all_tloss = []
epochs_steps = {}
model_best = 0
step = 0

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
        all_y.type(torch.int),
        (all_outputs > 0).type(torch.int),
    )

    steps_of_val.append(step)
    all_vloss.append(np.mean(losses_batches))
    all_f1.append(f_1)
    all_lr.append(optimizer.param_groups[0]["lr"])

    model.train()

    return np.mean(losses_batches), np.sum(corrects) / all_y.shape[0], f_1


def set_task():
    config.TASK = sorted(os.listdir(Path(config.PATH_TO_TASKS)))[-1]
    logger.debug('Task set to: %s' % config.TASK)


if __name__ == "__main__":

    logger.debug('Main of trainer_v2 started')
    logger.debug('Set config values')

    config.BATCH_SIZE = int(os.environ['BATCH_SIZE'])
    config.NUM_EPOCHS = 1000#int(os.environ['NUM_EPOCHS'])
    config.FOLD = int(os.environ['FOLD'])

    logger.debug(f"Set task: {os.environ['RUN_ID']}")

    config.TASK = os.environ['RUN_ID']

    logger.debug('Train dir set to: %s' % os.environ['BATCHES_INPUT_DIR'])

    config.TRAIN_DIR = os.environ['BATCHES_INPUT_DIR']

    config.RESULTS_DIR = Path(config.PATH_TO_RESULTS, config.TASK)
    logger.debug('Results dir set to: %s' % config.RESULTS_DIR)

    os.makedirs(config.RESULTS_DIR, exist_ok=True)

    # set patch size
    tuple_from_string = ast.literal_eval(os.environ['PATCH_SIZE'])
    patch_size = np.array(tuple_from_string)

    config.PATCH_SIZE = patch_size
    logger.debug(f"Patchsize set to: {patch_size}")

    # set and create checkpoint path

    config.CHECKPOINT_PATH = os.path.join(
        config.RESULTS_DIR, "resnet_18"
    )

    logger.debug('Create directories for results')

    os.makedirs(config.CHECKPOINT_PATH, exist_ok=True)
    os.makedirs(
        os.path.join(config.CHECKPOINT_PATH, "fold_%d" % config.FOLD), exist_ok=True
    )

    logger.debug('Directories created: %s' % config.CHECKPOINT_PATH)

    # load model

    model = resnet.generate_model(
            model_depth=18,
            n_classes=len(TAG_TO_CLASS_MAPPING) - 1,
            n_input_channels=config.NUM_INPUT_CHANNELS,
            shortcut_type="B",
            conv1_t_size=3,
            conv1_t_stride=1,
            no_max_pool=True,
            widen_factor=1.0,
        )

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    model = model.to(device)

    logger.debug('Load model on gpu')

    model.train()

    logger.debug('Get train/val split and load batchgenerators')

    train_samples, val_samples = ClassificationDataset.get_split()

    # class to uid mapping

    tag_to_uid_mapping = {}

    for tag in TAG_TO_CLASS_MAPPING.keys():
        tag_to_uid_mapping[tag] = OpenSearchHelper.get_list_of_uids_of_tag(tag)

    # uids to class mapping

    uid_to_tag_mapping = {uid: TAG_TO_CLASS_MAPPING[tag] for tag, uids in tag_to_uid_mapping.items() for uid in uids}

    transform = ClassificationDataset.get_train_transform(config.PATCH_SIZE)

    dl_train = ClassificationDataset(
        train_samples,
        config.BATCH_SIZE,
        config.PATCH_SIZE,
        config.NUM_WORKERS,
        seed_for_shuffle=config.FOLD,
        return_incomplete=False,
        shuffle=True,
        uid_to_tag_mapping=uid_to_tag_mapping,
    )

    mt_train = MultiThreadedAugmenter(
        data_loader=dl_train,
        transform=transform,
        num_processes=config.NUM_WORKERS,
        num_cached_per_queue=4,
        pin_memory=True,
    )

    dl_val = ClassificationDataset(
        val_samples,
        config.BATCH_SIZE,
        config.PATCH_SIZE,
        config.NUM_WORKERS,
        return_incomplete=False,
        shuffle=False,
        uid_to_tag_mapping=uid_to_tag_mapping,
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
        model.parameters(), lr=1e-3, momentum=0.9, weight_decay=5e-4
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=config.NUM_EPOCHS, eta_min=1e-10
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
    best_ema_f1 = 0
    ema_f1 = None
    gamma = 0.1

    # Train loop

    logger.debug('Train loop')

    mt_train._start()
    mt_val._start()

    for epoch in range(0, config.NUM_EPOCHS):

        logger.debug('Current epoch: %s' % str(epoch))

        train_loss = train_fn(model, criterion, mt_train, optimizer, scheduler, epoch)

        logger.debug('Train Loss: %s' % str(train_loss))

        val_loss, corrects, f1 = evaluate(model, epoch, mt_val, train_loss)

        ema_f1 = f1 if ema_f1 is None else gamma * f1 + (1 - gamma) * ema_f1

        logger.debug('Val Loss: %s' % str(val_loss))

        logger.debug(f'EMA F1: {ema_f1}')
        logger.debug(f'Accuracy: {corrects}')

        writer.add_scalar("train_loss", train_loss, global_step=epoch)
        writer.add_scalar("val_loss", val_loss, global_step=epoch)
        writer.add_scalar("val_acc", corrects, global_step=epoch)
        writer.add_scalar("ema_f1", ema_f1, global_step=epoch)
        writer.add_scalar(
            "learning_rate", optimizer.param_groups[0]["lr"], global_step=epoch
        )

        if ema_f1 > best_ema_f1 and len(all_steps) > config.SAVE_MODEL_START_STEP:
            best_ema_f1 = ema_f1
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

    mt_train._finish()
    mt_val._finish()