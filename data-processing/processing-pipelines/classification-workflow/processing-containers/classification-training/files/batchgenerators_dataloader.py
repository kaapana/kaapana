#!/usr/bin/env python3
import os
import random
import numpy as np

from batchgenerators.dataloading.data_loader import DataLoader
from batchgenerators.transforms.abstract_transforms import Compose
from batchgenerators.transforms.spatial_transforms import SpatialTransform_2

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
)

class ClassificationDataset(DataLoader):

    def __init__(self, data, batch_size, patch_size, num_threads_in_multithreaded, seed_for_shuffle=1234,
                 return_incomplete=False, shuffle=True, uid_to_tag_mapping=None, num_modalities=1, num_classes=1):
        super().__init__(data, batch_size, num_threads_in_multithreaded, seed_for_shuffle, return_incomplete, shuffle,
                         False)

        self.patch_size = patch_size
        self.num_modalities = num_modalities
        self.indices = list(range(len(self._data)))
        self.uid_to_tag_mapping = uid_to_tag_mapping
        self.seed_for_shuffle = seed_for_shuffle
        self.num_classes = num_classes

    def __len__(self):
        return len(self._data)

    def generate_train_batch(self):
        idx = self.get_indices()
        patients_for_batch = [self._data[i] for i in idx]

        # initialize empty array for data and seg
        data = np.zeros((self.batch_size, self.num_modalities, *self.patch_size), dtype=np.float32)
        seg = np.zeros((self.batch_size, self.num_classes), dtype="int16")

        for i, j in enumerate(patients_for_batch):
            input_image_path = os.path.join(os.environ['BATCHES_INPUT_DIR'], j, os.environ['OPERATOR_IN_DIR'], j + '.npy')
            input_image = np.load(input_image_path, mmap_mode="r")

            if os.environ['TASK'] == "binary":
                seg[i] = np.array(self.uid_to_tag_mapping[j])
            else:
                # Convert to one-hot encoding
                one_hot_np = np.eye(self.num_classes)[np.array(self.uid_to_tag_mapping[j])]  # Assuming 3 classes

                # Apply logical OR operation along the first dimension
                combined_one_hot = one_hot_np.any(axis=0).astype(int)
                seg[i] = combined_one_hot

            data[i] = input_image
            
        
        return {'data': data, 'class': seg, "sample": j}

    @staticmethod
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

    @staticmethod
    def get_split(random_seed):
        random.seed(random_seed)

        all_samples = os.listdir(os.environ['BATCHES_INPUT_DIR'])

        if len(all_samples) == 0:
            raise ValueError('No images in path: %s' % os.environ['BATCHES_INPUT_DIR'])

        percentage_val_samples = 15
        # 15% val. data

        num_val_samples = max(int(len(all_samples) / 100 * percentage_val_samples), 1)
        val_samples = random.sample(all_samples, num_val_samples)

        train_samples = list(filter(lambda sample: sample not in val_samples, all_samples))

        return train_samples, val_samples