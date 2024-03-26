#!/usr/bin/env python3
import os
import random
import numpy as np

from batchgenerators.dataloading.data_loader import DataLoader
from batchgenerators.transforms.abstract_transforms import Compose
from batchgenerators.transforms.color_transforms import (
    BrightnessMultiplicativeTransform,
    ContrastAugmentationTransform,
    GammaTransform,
)
from batchgenerators.transforms.noise_transforms import (
    GaussianBlurTransform,
    GaussianNoiseTransform,
)
from batchgenerators.transforms.resample_transforms import (
    SimulateLowResolutionTransform,
)
from batchgenerators.transforms.spatial_transforms import (
    MirrorTransform,
    SpatialTransform,
)

def configure_rotation_and_mirroring(patch_size):
    dim = len(patch_size)

    if dim == 2:
        if max(patch_size) / min(patch_size) > 1.5:
            rotation_for_DA = {
                "x": (-15.0 / 360 * 2.0 * np.pi, 15.0 / 360 * 2.0 * np.pi),
                "y": (0, 0),
                "z": (0, 0),
            }
        else:
            rotation_for_DA = {
                "x": (-180.0 / 360 * 2.0 * np.pi, 180.0 / 360 * 2.0 * np.pi),
                "y": (0, 0),
                "z": (0, 0),
            }
        mirror_axes = (0, 1)
    elif dim == 3:
        rotation_for_DA = {
            "x": (-30.0 / 360 * 2.0 * np.pi, 30.0 / 360 * 2.0 * np.pi),
            "y": (-30.0 / 360 * 2.0 * np.pi, 30.0 / 360 * 2.0 * np.pi),
            "z": (-30.0 / 360 * 2.0 * np.pi, 30.0 / 360 * 2.0 * np.pi),
        }
        mirror_axes = (0, 1, 2)
    else:
        raise RuntimeError()

    return rotation_for_DA, mirror_axes


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
        uid_to_tag_mapping=None,
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
        self.uid_to_tag_mapping = uid_to_tag_mapping
        self.seed_for_shuffle = seed_for_shuffle
        self.num_classes = num_classes

        # Check if all uids have a tag

        for uid in self._data:
            if uid not in self.uid_to_tag_mapping:
                raise ValueError(f"UID {uid} not found in tag mapping")

    def __len__(self):
        return len(self._data)

    def generate_train_batch(self):
        idx = self.get_indices()
        patients_for_batch = [self._data[i] for i in idx]

        # initialize empty array for data and seg
        data = np.zeros(
            (self.batch_size, self.num_modalities, *self.patch_size), dtype=np.float32
        )
        seg = np.zeros((self.batch_size, self.num_classes), dtype="int16")

        for i, j in enumerate(patients_for_batch):
            input_image_path = os.path.join(
                os.environ["BATCHES_INPUT_DIR"],
                j,
                os.environ["OPERATOR_IN_DIR"],
                j + ".npy",
            )
            input_image = np.load(input_image_path, mmap_mode="r")

            if os.environ["TASK"] == "binary":
                seg[i] = np.array(self.uid_to_tag_mapping[j])
            else:
                # Convert to one-hot encoding
                one_hot_np = np.eye(self.num_classes)[
                    np.array(self.uid_to_tag_mapping[j])
                ]

                # Apply logical OR operation along the first dimension
                combined_one_hot = one_hot_np.any(axis=0).astype(int)
                seg[i] = combined_one_hot

            data[i] = input_image

        return {"data": data, "class": seg, "sample": j}

    @staticmethod
    def get_train_transform(patch_size):
        rotation_for_DA, mirror_axes = configure_rotation_and_mirroring(patch_size)

        tr_transforms = []

        ignore_axes = None

        tr_transforms.append(
            SpatialTransform(
                patch_size,
                patch_center_dist_from_border=None,
                do_elastic_deform=False,
                alpha=(0, 0),
                sigma=(0, 0),
                do_rotation=True,
                angle_x=rotation_for_DA["x"],
                angle_y=rotation_for_DA["y"],
                angle_z=rotation_for_DA["z"],
                p_rot_per_axis=1,  # todo experiment with this
                do_scale=True,
                scale=(0.7, 1.4),
                border_mode_data="constant",
                border_cval_data=0,
                order_data=3,
                border_mode_seg="constant",
                border_cval_seg=1,
                order_seg=1,
                random_crop=False,  # random cropping is part of our dataloaders
                p_el_per_sample=0,
                p_scale_per_sample=0.2,
                p_rot_per_sample=0.2,
                independent_scale_for_each_axis=False,  # todo experiment with this
            )
        )

        tr_transforms.append(GaussianNoiseTransform(p_per_sample=0.1))
        tr_transforms.append(
            GaussianBlurTransform(
                (0.5, 1.0),
                different_sigma_per_channel=True,
                p_per_sample=0.2,
                p_per_channel=0.5,
            )
        )
        tr_transforms.append(
            BrightnessMultiplicativeTransform(
                multiplier_range=(0.75, 1.25), p_per_sample=0.15
            )
        )
        tr_transforms.append(ContrastAugmentationTransform(p_per_sample=0.15))
        tr_transforms.append(
            SimulateLowResolutionTransform(
                zoom_range=(0.5, 1),
                per_channel=True,
                p_per_channel=0.5,
                order_downsample=0,
                order_upsample=3,
                p_per_sample=0.25,
                ignore_axes=ignore_axes,
            )
        )
        tr_transforms.append(
            GammaTransform((0.7, 1.5), True, True, retain_stats=True, p_per_sample=0.1)
        )
        tr_transforms.append(
            GammaTransform((0.7, 1.5), False, True, retain_stats=True, p_per_sample=0.3)
        )

        if mirror_axes is not None and len(mirror_axes) > 0:
            tr_transforms.append(MirrorTransform(mirror_axes))

        tr_transforms = Compose(tr_transforms)

        return tr_transforms

    @staticmethod
    def get_split(random_seed):
        random.seed(random_seed)

        all_samples = os.listdir(os.environ["BATCHES_INPUT_DIR"])

        if len(all_samples) == 0:
            raise ValueError("No images in path: %s" % os.environ["BATCHES_INPUT_DIR"])

        percentage_val_samples = 15
        # 15% val. data

        num_val_samples = max(int(len(all_samples) / 100 * percentage_val_samples), 1)
        val_samples = random.sample(all_samples, num_val_samples)

        train_samples = list(
            filter(lambda sample: sample not in val_samples, all_samples)
        )

        return train_samples, val_samples
