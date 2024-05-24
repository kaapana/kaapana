import os
import ast
import json
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
    val = os.getenv(env_var, "")

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
    )  # get the actual values as a str, i.e. "['firstorder', 'shape2D']"
    value_literal = (
        ast.literal_eval(value_str) if value_str.lower() != "none" else None
    )  # convert string to python expression, i.e. ['firstorder', 'shape2D']
    assert value_literal is not None

    value_list: list = list(
        value_literal
    )  # make it an actual list, i.e. ['firstorder', 'shape2D']
    return value_list


def get_paths():
    """
    Set up input and output directories based on environment variables.
    These directory values are passed by default via Kaapana Airflow plugin.

    Returns:
        tuple: Input and output paths.
    """

    workflow_dir = get_env_str("WORKFLOW_DIR")
    in_dir = get_env_str("OPERATOR_IN_DIR")
    out_dir = get_env_str("OPERATOR_OUT_DIR")

    in_path = os.path.join("/", workflow_dir, in_dir)
    out_path = os.path.join("/", workflow_dir, out_dir)

    return in_path, out_path


def get_feature_classes():
    """
    Get the feature classes selected by the user in the UI form of the DAG.
    Kaapana Airflow plugin passes all UI form properties of the DAG as env vars inside operators.

    Returns:
        list: List of selected feature classes.
    """
    # this env var specifies the property key inside the UI form, i.e. FEATURE_CLASS_PROP_KEY="feature_classes"
    feature_classes_key = get_env_str("FEATURE_CLASS_PROP_KEY")

    # get the actual list stored in key, i.e. FEATURE_CLASSES=""['firstorder', 'shape2D']"
    feature_classes = get_env_list(feature_classes_key)

    return feature_classes


# Main script execution starts here

### PATHS ###
in_path, out_path = get_paths()


### FEATURE CLASSES ###
feature_classes = get_feature_classes()


# Initialize an extractor object with selected feature classes
feature_classes_dict = {feature_class: [] for feature_class in feature_classes}
extractor = featureextractor.RadiomicsFeatureExtractor(**feature_classes_dict)

# Process each nifti in the input folder
for file_name in os.listdir(in_path):
    if file_name.endswith(".nii") or file_name.endswith(".nii.gz"):
        print(f"extracting radiomics features of {file_name}")
        file_path = os.path.join(in_path, file_name)

        # load image
        image = sitk.ReadImage(file_path)

        # extract features (using the entire image)
        features = extractor.execute(image, image)

        # save features as json
        output_file = os.path.join(
            out_path, f"{os.path.splitext(file_name)[0]}_features.json"
        )
        with open(output_file, "w") as json_file:
            json.dump(features, json_file, indent=4)

        print(
            f"PyRadiomics feature extraction completed for {file_name}, results saved in {output_file}"
        )
