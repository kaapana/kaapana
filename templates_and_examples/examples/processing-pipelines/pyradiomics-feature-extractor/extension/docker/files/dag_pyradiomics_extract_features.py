from datetime import timedelta

from airflow.utils.dates import days_ago
from airflow.models import DAG

# Operators available under Kaapana library
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

# Operators specific to this DAG
from pyradiomics_extractor.PyradiomicsExtractorOperator import (
    PyradiomicsExtractorOperator,
)

# UI form that is shown under 'Workflow Execution' page for this DAG
ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "feature_classes": {
                "title": "Feature Classes to Extract",
                "description": "Select the radiomics feature classes to extract. More information at https://pyradiomics.readthedocs.io/en/latest/features.html",
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "firstorder",  # First Order Statistics
                        "shape",  # Shape-Based Features (3D)
                        "shape2D",  # Shape-Based Features (2D)
                        "glcm",  # Gray Level Co-occurrence Matrix Features
                        "glrlm",  # Gray Level Run Length Matrix Features
                        "glszm",  # Gray Level Size Zone Matrix Features
                        "ngtdm",  # Neighboring Gray Tone Difference Matrix Features
                        "gldm",  # Gray Level Dependence Matrix Features
                    ],
                },
            }
        },
    }
}

# Airflow DAG arguments
args = {
    "ui_forms": ui_forms,
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

# Airflow DAG instance
dag = DAG(
    dag_id="pyradiomics-extract-features", default_args=args, schedule_interval=None
)

# Get dicom files from the PACS
get_input = LocalGetInputDataOperator(dag=dag)

# Convert dicom data to specified format (nifti or nrrd)
convert_to_nifti = DcmConverterOperator(
    dag=dag, input_operator=get_input, output_format="nii.gz"
)

# Pyradiomics Extractor Operator that extracts radiomics features from nifti files
pyradiomics_extractor = PyradiomicsExtractorOperator(
    dag=dag,
    input_operator=convert_to_nifti,
    feature_class_prop_key="feature_classes",  # key inside ui form that contains feature classes
    # dev_server="code-server" # allows for debugging inside the container via a VSCode instance accessible under 'Pending Applications' page
)

# Minio Operator for putting json results to a specified Minio bucket
put_json_to_minio = LocalMinioOperator(
    dag=dag,
    name="put-json-to-minio",
    bucket_name="pyradiomics-features",
    action="put",
    action_operators=[pyradiomics_extractor],
    file_white_tuples=(".json"),
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> convert_to_nifti >> pyradiomics_extractor >> put_json_to_minio >> clean
