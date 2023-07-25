import os
import numpy as np
import nrrd
import json
from skimage.transform import resize
from statistics import median

class Normalizer:
    def normalize(self, image):
        raise NotImplementedError


class ZScoreNormalizer(Normalizer):
    def normalize(self, image, mask=None):
        if mask is not None:
            mean = np.mean(image[mask])
            std = np.std(image[mask])
            return np.where(mask, (image - mean) / std, image)
        else:
            return (image - np.mean(image)) / np.std(image)


class CTNormalizer(Normalizer):
    def normalize(self, image, lower, upper):
        image = np.clip(image, lower, upper)
        return (image - lower) / (upper - lower)


class NoNormalizer(Normalizer):
    def normalize(self, image, target_dtype=np.float32):
        return image.astype(target_dtype)


class RescaleTo01Normalizer(Normalizer):
    def normalize(self, image):
        return (image - np.min(image)) / (np.max(image) - np.min(image))


class RGBTo01Normalizer(Normalizer):
    def normalize(self, image):
        return image / 255.0

def load_nrrd(file_path):
    data, header = nrrd.read(file_path)
    return data, header

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

def compute_spacing(header):
    spacings = np.diag(header['space directions']).tolist() 
    return [abs(i) for i in np.diag(header['space directions']).tolist()]

def compute_new_shape(old_shape, old_spacing, new_spacing):
    new_shape = np.array([int(round(i / j * k)) for i, j, k in zip(old_spacing, new_spacing, old_shape)])
    return new_shape

def resample_image(data, current_spacing, new_spacing, order=3):
    assert len(data.shape) in [2, 3], "data must be 2D (x, y) or 3D (x, y, z)"

    new_shape = compute_new_shape(data.shape, current_spacing, new_spacing)
    
    # Resize using skimage
    resized = resize(data, new_shape, order, mode='edge', anti_aliasing=False)
    return resized

def get_medians(dataset_folder):
    median_spacings = []
    for patient_folder in os.listdir(dataset_folder):
        patient_path = os.path.join(dataset_folder, patient_folder, "dcm-converter")
        for file_name in os.listdir(patient_path):
            if file_name.endswith('.nrrd'):
                file_path = os.path.join(patient_path, file_name)
                _, header = load_nrrd(file_path)
                spacings = compute_spacing(header)
                median_spacings.append(median(spacings))
    return median_spacings

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

def select_normalization_method(dataset_stats):
    selected_normalization_methods = {}

    # Extracting relevant statistics
    max_pixel_intensity = dataset_stats['max']
    min_pixel_intensity = dataset_stats['min']
    std_dev = dataset_stats['std']
    dimensions = dataset_stats['dimensions']

    # 1. If the dataset has a wide range of pixel values, use CTNormalizer
    if max_pixel_intensity - min_pixel_intensity > 255:
        return CTNormalizer

    # 2. If the dataset has high standard deviation, use ZScoreNormalizer
    elif std_dev > 1:
        return ZScoreNormalizer

    # 3. If the dataset has a normal range of pixel values (0-255), use RescaleTo01Normalizer
    elif 0 <= min_pixel_intensity and max_pixel_intensity <= 255:
        return RescaleTo01Normalizer

    # 4. If none of the above conditions are met, don't apply normalization
    else:
        return NoNormalizer


def process_dataset(dataset_folder, target_spacing):
    results = {}
    spacings_list = []
    for patient_folder in os.listdir(dataset_folder):
        patient_path = os.path.join(dataset_folder, patient_folder, "dcm-converter")
        for file_name in os.listdir(patient_path):
            if file_name.endswith('.nrrd'):
                file_path = os.path.join(patient_path, file_name)
                data, header = load_nrrd(file_path)
                spacings = compute_spacing(header)
                spacings_list.append(spacings)
                stats = compute_statistics(data)
                stats['spacings'] = spacings
                target_spacing = get_target_spacing(spacings_list, target_spacing, data.shape)
                stats['spacing_after_resampling'] = target_spacing
                results[file_name] = stats

    lower_percentiles = [stats['percentile_00_5'] for stats in results.values()]
    upper_percentiles = [stats['percentile_99_5'] for stats in results.values()]

    common_lower_percentile = np.max(lower_percentiles)
    common_upper_percentile = np.min(upper_percentiles)

    for patient_folder in os.listdir(dataset_folder):
        patient_path = os.path.join(dataset_folder, patient_folder, "dcm-converter")
        for file_name in os.listdir(patient_path):
            if file_name.endswith('.nrrd'):
                file_path = os.path.join(patient_path, file_name)
                data, header = load_nrrd(file_path)

                # Normalize and resample together
                normalizer = select_normalization_method(results[file_name])
                normalizer = normalizer()

                # Resample
                data_resampled = resample_image(data, stats['spacings'], stats['spacing_after_resampling'])
                
                if isinstance(normalizer, CTNormalizer):
                    # Normalize
                    data_normalized = normalizer.normalize(data_resampled, lower=common_lower_percentile, upper=common_upper_percentile)
                else:
                    data_normalized = normalizer.normalize(data_resampled)

                target_dir = os.path.join(dataset_folder, patient_folder, "classification-training")
                os.makedirs(target_dir, exist_ok=True)
                np.save(os.path.join(target_dir, patient_folder + ".npy"), data_normalized)



    return results

training = os.listdir("/kaapana/mounted/data")[0]
dataset_folder = os.path.join("/kaapana/mounted/data", training, "batch")
median_spacings = get_medians(dataset_folder)
new_spacing = [median(median_spacings)] * 3

dataset_stats = process_dataset(dataset_folder, new_spacing)

# To save results in a file
with open(os.path.join("mounted/data", training, "conf",'dataset_stats.json'), 'w') as outfile:
    json.dump(dataset_stats, outfile)

