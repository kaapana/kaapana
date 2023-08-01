#!/usr/bin/env python3
import os
import random

import numpy as np
from batchgenerators.dataloading.data_loader import DataLoader
from batchgenerators.transforms.abstract_transforms import Compose
from batchgenerators.transforms.spatial_transforms import SpatialTransform_2

import classification_config as config
from skimage.transform import resize

class FolderFilenameStructuredClassificationDataset(DataLoader):

    def __init__(self, data, batch_size, patch_size, num_threads_in_multithreaded, seed_for_shuffle=1234,
                 return_incomplete=False,
                 shuffle=True):
        super().__init__(data, batch_size, num_threads_in_multithreaded, seed_for_shuffle, return_incomplete, shuffle,
                         False)

        self.patch_size = patch_size
        self.num_modalities = config.NUM_INPUT_CHANNELS
        self.indices = list(range(len(self._data)))

    def __len__(self):
        return len(self._data)

    def generate_train_batch(self):
        idx = self.get_indices()
        patients_for_batch = [self._data[i] for i in idx]

        # initialize empty array for data and seg
        data = np.zeros((self.batch_size, self.num_modalities, *self.patch_size), dtype=np.float32)
        seg = np.zeros((self.batch_size, 1), dtype="int16")

        for i, j in enumerate(patients_for_batch):
            input_image_path = os.path.join(config.TRAIN_DIR, j, os.environ['OPERATOR_IN_DIR'], j + '.npy')
            input_image = np.load(input_image_path, mmap_mode="r")

            output_image = 1

            data[i] = input_image
            seg[i] = output_image
        
        return {'data': data, 'class': seg, "sample": j}


def get_train_transform(patch_size):
    tr_transforms = []

    tr_transforms.append(
        SpatialTransform_2(
            patch_size, [i // 2 for i in patch_size],
            do_elastic_deform=False,
            do_rotation=True,
            do_scale=False,
            random_crop=False,
            p_rot_per_sample=0.66,
        )
    )

    tr_transforms = Compose([])
    return tr_transforms


def get_split():
    random.seed(config.FOLD)

    all_samples = os.listdir(config.TRAIN_DIR)

    percentage_val_samples = 20

    num_val_samples = int(len(all_samples) / 100 * percentage_val_samples)
    val_samples = random.sample(all_samples, num_val_samples)

    train_samples = list(filter(lambda sample: sample not in val_samples, all_samples))

    return train_samples, val_samples