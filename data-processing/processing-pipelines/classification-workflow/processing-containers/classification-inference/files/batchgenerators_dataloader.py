#!/usr/bin/env python3
import os

import numpy as np
from batchgenerators.dataloading.data_loader import DataLoader


class ClassificationDataset(DataLoader):
    def __init__(
        self,
        data,
        batch_size,
        patch_size,
        num_threads_in_multithreaded,
        seed_for_shuffle=1234,
        return_incomplete=False,
        shuffle=True,
        num_modalities=1,
        num_classes=1,
    ):
        super().__init__(
            data,
            batch_size,
            num_threads_in_multithreaded,
            seed_for_shuffle,
            return_incomplete,
            shuffle,
            False,
        )

        self.patch_size = patch_size
        self.num_modalities = num_modalities
        self.indices = list(range(len(self._data)))
        self.seed_for_shuffle = seed_for_shuffle
        self.num_classes = num_classes

    def __len__(self):
        return len(self._data)

    def generate_train_batch(self):
        idx = self.get_indices()
        patients_for_batch = [self._data[i] for i in idx]
        samples = {}
        # initialize empty array for data and seg
        data = np.zeros(
            (self.batch_size, self.num_modalities, *self.patch_size), dtype=np.float32
        )

        for i, j in enumerate(patients_for_batch):
            input_image_path = os.path.join(
                os.environ["BATCHES_INPUT_DIR"],
                j,
                os.environ["OPERATOR_IN_DIR"],
                j + ".npy",
            )
            input_image = np.load(input_image_path, mmap_mode="r")

            data[i] = input_image
            samples[i] = j

        return {"data": data, "samples": samples}
