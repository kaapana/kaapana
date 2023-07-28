import os
import numpy as np
import nrrd
import json
from skimage.transform import resize
from statistics import median
import SimpleITK as sitk

class Normalizer:
    def normalize(self, image):
        raise NotImplementedError

class ZScoreNormalizer(Normalizer):
    def normalize(self, image, mask=None):
        return (image - np.mean(image)) / np.std(image)

def compute_statistics(data):
    stats = {}
    stats['dimensions'] = data.shape
    stats['mean'] = float(np.mean(data))
    stats['median'] = float(np.median(data))
    stats['std'] = float(np.std(data))
    stats['min'] = float(np.min(data))
    stats['max'] = float(np.max(data))
    stats['percentile_99_5'] = float(np.percentile(data, 99.5))
    stats['percentile_00_5'] = float(np.percentile(data, 0.5))
    return stats

def resample_image(patient, order=3):
    assert len(patient['stats']['dimensions']) in [2, 3], "data must be 2D (x, y) or 3D (x, y, z)"

    old_shape = np.array(patient['stats']['dimensions'])
    old_spacing = np.array(patient['stats']['spacing'])
    new_spacing = np.array(patient['stats']['spacing_after_resampling'])
    
    new_shape = np.array([int(round(i / j * k)) for i, j, k in zip(old_spacing, new_spacing, old_shape)])
    
    # Resize using skimage
    resized = resize(sitk.GetArrayFromImage(patient['image']), new_shape, order=order, mode='edge', anti_aliasing=False, preserve_range=True)
    return resized


def get_target_spacing(spacings, target, target_size, anisotropy_threshold=3.0):
    worst_spacing_axis = np.argmax(target)
    other_axes = [i for i in range(len(target)) if i != worst_spacing_axis]
    other_spacings = [target[i] for i in other_axes]
    other_sizes = [target_size[i] for i in other_axes]

    has_aniso_spacing = target[worst_spacing_axis] > (anisotropy_threshold * max(other_spacings))
    has_aniso_voxels = target_size[worst_spacing_axis] * anisotropy_threshold < min(other_sizes)

    if has_aniso_spacing and has_aniso_voxels:
        spacings_of_that_axis = np.vstack(spacings)[:, worst_spacing_axis]
        target_spacing_of_that_axis = np.percentile(spacings_of_that_axis, 10)
        
        # don't let the spacing of that axis get higher than the other axes
        if target_spacing_of_that_axis < max(other_spacings):
            target_spacing_of_that_axis = max(max(other_spacings), target_spacing_of_that_axis) + 1e-5
        target[worst_spacing_axis] = target_spacing_of_that_axis
    return target

if __name__ == "__main__":

    batch = {}

    spacings  = []
    spacing_x = []
    spacing_y = []
    spacing_z = []

    for patient in os.listdir(os.environ['BATCHES_INPUT_DIR']):
        patient_dict = {}

        patient_dict["image"] = sitk.ReadImage(os.path.join(os.environ['BATCHES_INPUT_DIR'], patient, "dcm-converter", patient + ".nrrd"))

        spacing = patient_dict["image"].GetSpacing()

        if len(spacing) > 3:
            raise ValueError("Not covering the scope of >3-dimensional arrays: E.g. 2 images in one")

        spacing_x.append(spacing[0])
        spacing_y.append(spacing[1])
        spacing_z.append(spacing[2])
        spacings.append(spacing)

        patient_dict["stats"] = compute_statistics(sitk.GetArrayFromImage(patient_dict["image"]))
        patient_dict["stats"]["spacing"] = spacing
        
        batch[patient] = patient_dict

    median_spacing = list((np.median(np.array(spacing_x)), np.median(np.array(spacing_y)), np.median(np.array(spacing_z))))

    for patient in batch.keys():
        target_spacing = get_target_spacing(spacings, median_spacing, batch[patient]['image'].GetSize())
        batch[patient]['stats']['spacing_after_resampling'] = target_spacing
        
        # Resample
        data_resampled = resample_image(batch[patient])

        # Normalize
        normalizer = ZScoreNormalizer()
        data_normalized = normalizer.normalize(data_resampled)

        target_dir = os.path.join(os.environ['BATCHES_INPUT_DIR'], patient, "classification-training")
        os.makedirs(target_dir, exist_ok=True)
        np.save(os.path.join(target_dir, patient + ".npy"), data_normalized)
