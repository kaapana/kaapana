#!/usr/bin/env python3
import ast
import json
import logging
import os
from pathlib import Path

import numpy as np
import torch
from batchgenerators.dataloading.multi_threaded_augmenter import MultiThreadedAugmenter
from batchgenerators.transforms.abstract_transforms import Compose
from batchgenerators.transforms.sample_normalization_transforms import (
    ZeroMeanUnitVarianceTransform,
)
from batchgenerators_dataloader import ClassificationDataset
from monai.networks.nets import resnet18
from opensearch_helper import OpenSearchHelper
from torch.utils.tensorboard import SummaryWriter
from torchmetrics import Accuracy, F1Score

os.environ["FOLD"] = "0"

RESULTS_DIR = Path(
    "/models", os.environ["DAG_ID"], f"{os.environ['WORKFLOW_ID']}-fold-{os.environ['FOLD']}"
)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Create a custom logger
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)

f_handler = logging.FileHandler(Path(RESULTS_DIR, "training.log"))
f_handler.setLevel(logging.DEBUG)

c_format = logging.Formatter("%(levelname)s - %(message)s")
f_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
c_handler.setFormatter(c_format)
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(c_handler)
logger.addHandler(f_handler)

# Create mapping between classes and tags before logging

TAG_TO_CLASS_MAPPING = {}

for class_idx, tag in enumerate(sorted(ast.literal_eval(os.environ["TAG_TO_CLASS_MAPPING_JSON"]))):
    TAG_TO_CLASS_MAPPING[tag] = class_idx

# Log config

logger.debug(f"TAG_TO_CLASS_MAPPING_JSON={str(TAG_TO_CLASS_MAPPING)}")
logger.debug(f"TASK={os.environ['TASK']}")
logger.debug(f"NUM_EPOCHS={os.environ['NUM_EPOCHS']}")
logger.debug(f"DIMENSIONS={os.environ['DIMENSIONS']}")
logger.debug(f"PATCH_SIZE={os.environ['PATCH_SIZE']}")
logger.debug(f"BATCH_SIZE={os.environ['BATCH_SIZE']}")
logger.debug(f"TASK={os.environ['TASK']}")

# Save config for inference

try:
    data = {}

    data["TAG_TO_CLASS_MAPPING_JSON"] = str(TAG_TO_CLASS_MAPPING)
    data["TASK"] = os.environ["TASK"]
    data["NUM_EPOCHS"] = os.environ["NUM_EPOCHS"]
    data["DIMENSIONS"] = os.environ["DIMENSIONS"]
    data["PATCH_SIZE"] = os.environ["PATCH_SIZE"]
    data["BATCH_SIZE"] = os.environ["BATCH_SIZE"]
    data["TASK"] = os.environ["TASK"]
    data["WORKFLOW_ID"] = os.environ["WORKFLOW_ID"]
    data["FOLD"] = os.environ["FOLD"]

    with open(os.path.join(RESULTS_DIR, "config.json"), "w") as f:
        json.dump(data, f)

except json.JSONDecodeError:
    logger.error("Error decoding JSON")

# Config

NUM_CLASSES = 1 if os.environ["TASK"] == "binary" else len(TAG_TO_CLASS_MAPPING)
NUM_WORKERS = 4
NUM_INPUT_CHANNELS = 1
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

if os.environ["TASK"] == "multilabel":
    f1_metric = F1Score(task=os.environ["TASK"], num_labels=NUM_CLASSES).to(DEVICE)
    accuracy_metric = Accuracy(task=os.environ["TASK"], num_labels=NUM_CLASSES).to(
        DEVICE
    )
else:
    f1_metric = F1Score(task=os.environ["TASK"], num_classes=NUM_CLASSES + 1).to(DEVICE)
    accuracy_metric = Accuracy(task=os.environ["TASK"], num_classes=NUM_CLASSES + 1).to(
        DEVICE
    )


def save_checkpoint(model, optimizer, filename="my_checkpoint.pth.tar"):
    print("=> Saving checkpoint")
    checkpoint = {
        "state_dict": model.state_dict(),
        "optimizer": optimizer.state_dict(),
    }
    torch.save(checkpoint, filename)


def load_checkpoint(checkpoint_file, model, optimizer, lr):
    print("=> Loading checkpoint")
    checkpoint = torch.load(checkpoint_file, map_location=DEVICE)
    model.load_state_dict(checkpoint["state_dict"], strict=False)
    optimizer.load_state_dict(checkpoint["optimizer"])

    # If we don't do this then it will just have learning rate of old checkpoint
    # and it will lead to many hours of debugging \:
    for param_group in optimizer.param_groups:
        param_group["lr"] = lr


def train_fn(model, criterion, mt_train, optimizer, scheduler, epoch):
    losses_batches = []
    for batch_idx, batch in enumerate(mt_train):
        x = torch.from_numpy(batch["data"]).to(DEVICE)
        y = torch.from_numpy(batch["class"]).to(DEVICE)

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

    scheduler.step()

    return np.mean(losses_batches)


def evaluate(model, epoch, mt_val, train_loss):
    model.eval()
    losses_batches = []

    for batch_idx, batch in enumerate(mt_val):
        x = torch.from_numpy(batch["data"]).to(DEVICE)
        y = torch.from_numpy(batch["class"]).to(DEVICE)

        with torch.no_grad():
            outputs = model(x)
            loss = criterion(outputs.type(torch.float32), y.type(torch.float32))

            predictions = torch.round(torch.sigmoid(outputs))

            # Update F1Score metric
            f1_metric(predictions, y)
            accuracy_metric(predictions, y)

            losses_batches.append(loss.item())

    # Compute final F1 score
    f_1 = f1_metric.compute()
    accuracy = accuracy_metric.compute()

    model.train()

    return np.mean(losses_batches), accuracy, f_1


if __name__ == "__main__":
    logger.debug("Main of trainer_v3 started")
    logger.debug(f"Set task: {os.environ['RUN_ID']}")
    logger.debug("Train dir set to: %s" % os.environ["BATCHES_INPUT_DIR"])
    logger.debug("Results dir set to: %s" % RESULTS_DIR)

    # set patch size
    tuple_from_string = ast.literal_eval(os.environ["PATCH_SIZE"])
    patch_size = np.array(tuple_from_string)

    logger.debug(f"Patchsize set to: {patch_size}")

    # class to uid mapping

    tag_to_uid_mapping = {}

    for tag in TAG_TO_CLASS_MAPPING.keys():
        tag_to_uid_mapping[tag] = OpenSearchHelper.get_list_of_uids_of_tag(tag)

    # uids to class mapping

    uid_to_tag_mapping = {}

    for tag, uids in tag_to_uid_mapping.items():
        for uid in uids:
            if uid in uid_to_tag_mapping:
                uid_to_tag_mapping[uid].append(TAG_TO_CLASS_MAPPING[tag])
            else:
                uid_to_tag_mapping[uid] = [TAG_TO_CLASS_MAPPING[tag]]

    # load model

    spatial_dims = int(os.environ["DIMENSIONS"][0])

    model = resnet18(
        pretrained=False,
        progress=True,
        spatial_dims=spatial_dims,
        n_input_channels=NUM_INPUT_CHANNELS,
        num_classes=NUM_CLASSES,
    )

    model = model.to(DEVICE)

    logger.debug("Load model on gpu")

    model.train()

    # Get train/val split and load batchgenerators

    logger.debug("Get train/val split and load batchgenerators")
    train_samples, val_samples = ClassificationDataset.get_split(
        int(os.environ["FOLD"])
    )

    transform = ClassificationDataset.get_train_transform(patch_size)

    dl_train = ClassificationDataset(
        data=train_samples,
        batch_size=int(os.environ["BATCH_SIZE"]),
        patch_size=patch_size,
        num_threads_in_multithreaded=NUM_WORKERS,
        seed_for_shuffle=int(os.environ["FOLD"]),
        return_incomplete=False,
        shuffle=True,
        uid_to_tag_mapping=uid_to_tag_mapping,
        num_modalities=NUM_INPUT_CHANNELS,
        num_classes=NUM_CLASSES,
    )

    mt_train = MultiThreadedAugmenter(
        data_loader=dl_train,
        transform=transform,
        num_processes=NUM_WORKERS,
        num_cached_per_queue=4,
        pin_memory=True,
    )

    dl_val = ClassificationDataset(
        data=val_samples,
        batch_size=int(os.environ["BATCH_SIZE"]),
        patch_size=patch_size,
        num_threads_in_multithreaded=NUM_WORKERS,
        return_incomplete=False,
        shuffle=False,
        uid_to_tag_mapping=uid_to_tag_mapping,
        num_modalities=NUM_INPUT_CHANNELS,
        num_classes=NUM_CLASSES,
    )

    mt_val = MultiThreadedAugmenter(
        data_loader=dl_val,
        transform=Compose([ZeroMeanUnitVarianceTransform()]),
        num_processes=NUM_WORKERS,
        num_cached_per_queue=4,
        pin_memory=True,
    )

    # Hyperparameters

    logger.debug("Set hyperparameters")

    if os.environ["TASK"] == "multiclass":
        criterion = torch.nn.CrossEntropyLoss()
    else:
        criterion = torch.nn.BCEWithLogitsLoss()

    optimizer = torch.optim.SGD(
        model.parameters(), lr=1e-3, momentum=0.9, weight_decay=5e-4
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=int(os.environ["NUM_EPOCHS"]), eta_min=1e-10
    )
    scaler = torch.cuda.amp.GradScaler()

    # Init Tensorboard

    logger.debug("Init Tensorboard")

    writer = SummaryWriter(os.path.join("/tensorboard", os.environ["RUN_ID"]))

    best_ema_f1 = 0
    ema_f1 = None
    gamma = 0.1

    # Train loop

    logger.debug("Train loop")

    mt_train._start()
    mt_val._start()

    for epoch in range(0, int(os.environ["NUM_EPOCHS"])):
        logger.debug("\nCurrent epoch: %s" % str(epoch))

        train_loss = train_fn(model, criterion, mt_train, optimizer, scheduler, epoch)

        logger.debug("Train Loss: %s" % str(train_loss))

        val_loss, corrects, f1 = evaluate(model, epoch, mt_val, train_loss)

        ema_f1 = f1 if ema_f1 is None else gamma * f1 + (1 - gamma) * ema_f1

        logger.debug("Val Loss: %s" % str(val_loss))

        logger.debug(f"EMA F1: {ema_f1}")
        logger.debug(f"Accuracy: {corrects}")

        writer.add_scalar("train_loss", train_loss, global_step=epoch)
        writer.add_scalar("val_loss", val_loss, global_step=epoch)
        writer.add_scalar("val_acc", corrects, global_step=epoch)
        writer.add_scalar("ema_f1", ema_f1, global_step=epoch)
        writer.add_scalar(
            "learning_rate", optimizer.param_groups[0]["lr"], global_step=epoch
        )

        if ema_f1 > best_ema_f1:
            best_ema_f1 = ema_f1

            logger.debug("Save checkpoint")

            save_checkpoint(
                model,
                optimizer,
                os.path.join(
                    RESULTS_DIR,
                    f"model-best.pth.tar",
                ),
            )

    logger.debug("Finished Training")

    save_checkpoint(
        model,
        optimizer,
        os.path.join(RESULTS_DIR, "model-end.pth.tar"),
    )

    mt_train._finish()
    mt_val._finish()
