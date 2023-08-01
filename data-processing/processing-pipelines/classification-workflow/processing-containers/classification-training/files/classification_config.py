#!/usr/bin/env python3
import torch

# Task details
TASK = ""  # If empty will be set with Task with the greatest index
FOLD = 0

# Input details
PATCH_SIZE = (128, 128, 128)
NUM_INPUT_CHANNELS = 1

# Training details
BATCH_SIZE = 1
NUM_WORKERS = 4
NUM_EPOCHS = 1000
SAVE_MODEL_START_STEP = 0
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Important paths
TRAIN_DIR = "/data/classification_training"
PATH_TO_DATA = "/data/classification-tasks"
PATH_TO_RESULTS = "/minio/classification-results"
CHECKPOINT_PATH = ""
RESULTS_DIR = ""
# Important names
CHECKPOINT = "model.pth.tar"
CHECKPOINT_BEST = "model_best.pth.tar"
TENSORBOARD_PATH = "/kaapana/mounted/tb-logs"