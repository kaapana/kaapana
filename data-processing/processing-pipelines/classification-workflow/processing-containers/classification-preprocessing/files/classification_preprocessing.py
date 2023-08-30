import os
import numpy as np
from skimage.transform import resize
import SimpleITK as sitk
import ast

class ZScoreNormalizer():
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

    tuple_from_string = ast.literal_eval(os.environ['PATCH_SIZE'])
    new_shape = np.array(tuple_from_string)
    resized = resize(sitk.GetArrayFromImage(patient['image']).squeeze(), new_shape, order=order, mode='edge', anti_aliasing=False, preserve_range=True)
    return resized

if __name__ == "__main__":

    batch = {}

    for patient in os.listdir(os.environ['BATCHES_INPUT_DIR']):
        patient_dict = {}

        patient_dict["image"] = sitk.ReadImage(os.path.join(os.environ['BATCHES_INPUT_DIR'], patient, "dcm-converter", patient + ".nrrd"))

        spacing = patient_dict["image"].GetSpacing()

        if len(spacing) > 3:
            raise ValueError("Not covering the scope of >3-dimensional arrays: E.g. 2 images in one")

        patient_dict["stats"] = compute_statistics(sitk.GetArrayFromImage(patient_dict["image"]))

        # Resample
        data_resampled = resample_image(patient_dict)

        # Normalize
        normalizer = ZScoreNormalizer()
        data_normalized = normalizer.normalize(data_resampled)

        target_dir = os.path.join(os.environ['BATCHES_INPUT_DIR'], patient, os.environ['OPERATOR_OUT_DIR'])
        os.makedirs(target_dir, exist_ok=True)
        np.save(os.path.join(target_dir, patient + ".npy"), data_normalized)
