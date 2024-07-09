import os
import ast
import json
import numpy as np
import SimpleITK as sitk
from radiomics import featureextractor


def get_env_str(env_var, can_be_empty=False) -> str:
    """
    Get string values from environment variables, ensuring they are not empty unless allowed.

    Parameters:
        env_var (str): The environment variable name.
        can_be_empty (bool): Whether the environment variable can be empty.

    Returns:
        str: The value of the environment variable.

    Raises:
        AssertionError: If the environment variable is empty and can_be_empty is False.
    """
    val = os.getenv(env_var.upper(), "")

    if can_be_empty is not True:
        assert val != "", f"ERROR: {env_var} is passed as empty, aborting"

    return val


def get_env_list(env_var):
    """
    Get list values from environment variables.

    Parameters:
        env_var (str): The environment variable name.

    Returns:
        list: The value of the environment variable as a list.
    """

    value_str = get_env_str(
        env_var
    )  # get the actual values as a str, e.g. "['firstorder', 'shape2D']"
    value_literal = (
        ast.literal_eval(value_str) if value_str.lower() != "none" else None
    )  # convert string to python expression, e.g. ['firstorder', 'shape2D']
    assert value_literal is not None

    value_list: list = list(
        value_literal
    )  # make it an actual list, e.g. ['firstorder', 'shape2D']
    return value_list


def get_batch_path():
    """
    Set up input batch directory based on environment variables.
    Batch dir contains multiple series uids folders, and each series contains operators as subfolders.
    Example:
    * batch_path = /kaapana/mounted/data/pyradiomics-extract-features-<time>/batch/
        * batch_path/<series_ins_uid_1>/get_input_data/*.dcm
        * batch_path/<series_ins_uid_1>/dcm_converter/<series_ins_uid_1>.nii.gz
        * batch_path/<series_ins_uid_2>/dcm_converter/<series_ins_uid_2>.nii.gz

    Returns:
        str: Batch path to iterate over for series uid folders.
    """

    workflow_dir = get_env_str("WORKFLOW_DIR")
    batch_dir = get_env_str("BATCH_NAME")

    batch_path = os.path.join("/", workflow_dir, batch_dir)

    return batch_path


def get_feature_classes():
    """
    Get the feature classes selected by the user in the UI form of the DAG.
    Kaapana Airflow plugin passes all UI form properties of the DAG as env vars inside operators.

    Returns:
        list: List of selected feature classes.
    """
    # this env var specifies the property key inside the UI form, e.g. FEATURE_CLASS_PROP_KEY="feature_classes"
    feature_classes_key = get_env_str("FEATURE_CLASS_PROP_KEY")

    # get the actual list stored in key, e.g. FEATURE_CLASSES=""['firstorder', 'shape2D']"
    feature_classes = get_env_list(feature_classes_key)

    return feature_classes

def convert_ndarray_to_list(d):
    """
    Convert any numpy ndarrays in a dictionary to lists.
    Useful for converting some of the output of pyradiomics feature extractor.
    """
    for key, value in d.items():
        if isinstance(value, np.ndarray):
            d[key] = value.tolist()
        elif isinstance(value, dict):
            d[key] = convert_ndarray_to_list(value)
    return d


# Main script execution starts here

### PATHS & DIRS ###
batch_path = (
    get_batch_path()
)  # i.e. /kaapana/mounted/data/pyradiomics-extract-features-<time>/batch/
in_operator = get_env_str(
    "OPERATOR_IN_DIR"
)  # Name of the input operator, e.g. dcm-converter
out_operator = get_env_str(
    "OPERATOR_OUT_DIR"
)  # Name of this operator as the output operator, e.g. pyradiomics-feature-extractor


### FEATURE CLASSES ###
feature_classes = get_feature_classes()


# Initialize an extractor object with selected feature classes
feature_classes_dict = {feature_class: [] for feature_class in feature_classes}
extractor = featureextractor.RadiomicsFeatureExtractor(**feature_classes_dict)

# Go through each data sample based on series instance uid
for series_ins_uid in os.listdir(batch_path):
    print(f"processing {series_ins_uid}")
    # generate input & output paths, e.g. /kaapana/mounted/data/pyradiomics-extract-features-<time>/batch/<series_ins_uid>/dcm-converter
    in_path = os.path.join(batch_path, series_ins_uid, in_operator)
    out_path = os.path.join(batch_path, series_ins_uid, out_operator)
    os.makedirs(out_path, exist_ok=True)  # Create output directory if it does not exist

    # Process every nifti file under input path
    for file_name in os.listdir(in_path):
        if file_name.endswith(".nii") or file_name.endswith(".nii.gz"):
            print(f"extracting radiomics features of {file_name}")
            file_path = os.path.join(in_path, file_name)

            # load image
            image = sitk.ReadImage(file_path)

            # extract features (using the entire image)
            features = extractor.execute(image, image)

            # convert all ndarrays in features to lists for json serialization
            features = convert_ndarray_to_list(features)

            # save features as json
            output_file = os.path.join(
                out_path, f"{series_ins_uid}_features.json"
            )
            print(f"output_file {output_file}")
            with open(output_file, "w") as json_file:
                json.dump(features, json_file, indent=4)

            print(
                f"PyRadiomics feature extraction completed for {file_name}, results saved in {output_file}"
            )
