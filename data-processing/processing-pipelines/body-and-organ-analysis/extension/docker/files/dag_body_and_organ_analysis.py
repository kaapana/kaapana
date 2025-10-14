from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.MinioOperator import MinioOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator

from body_and_organ_analysis.BodyAndOrganAnalysisOperator import (
    BodyAndOrganAnalysisOperator,
)
from body_and_organ_analysis.BoaOutputCheckOperator import BoaOutputCheckOperator

max_active_runs = 5


ui_forms = {
    "documentation_form": {
        "path": "/user_guide/extensions.html#body-and-organ-analysis",
    },
    "publication_form": {
        "type": "object",
        "properties": {
            "boa": {
                "title": "BOA",
                "default": "Haubold, J., Baldini, G., Parmar, V., Schaarschmidt, B. M., Koitka, S., Kroll, L., van Landeghem, N., Umutlu, L., Forsting, M., Nensa, F., & Hosch, R. (2023). BOA: A CT-Based Body and Organ Analysis for Radiologists at the Point of Care. Investigative radiology, 10.1097/RLI.0000000000001040. Advance online publication. https://doi.org/10.1097/RLI.0000000000001040",
                "description": "Haubold, J., Baldini, G., Parmar, V., Schaarschmidt, B. M., Koitka, S., Kroll, L., van Landeghem, N., Umutlu, L., Forsting, M., Nensa, F., & Hosch, R. (2023). BOA: A CT-Based Body and Organ Analysis for Radiologists at the Point of Care. Investigative radiology, 10.1097/RLI.0000000000001040. Advance online publication. https://doi.org/10.1097/RLI.0000000000001040",
                "type": "string",
                "readOnly": True,
            },
            "totalsegmentator": {
                "title": "TotalSegmentator",
                "default": "Wasserthal J, Breit H-C, Meyer MT, et al. TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images. Radiol. Artif. Intell. 2023:e230024. Available at: https://pubs.rsna.org/doi/10.1148/ryai.230024.",
                "description": "Wasserthal J, Breit H-C, Meyer MT, et al. TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images. Radiol. Artif. Intell. 2023:e230024. Available at: https://pubs.rsna.org/doi/10.1148/ryai.230024.",
                "type": "string",
                "readOnly": True,
            },
            "nnunet": {
                "title": "nnU-Net",
                "default": "Isensee F, Jaeger PF, Kohl SAA, et al. nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation. Nat. Methods. 2021;18(2):203–211. Available at: https://www.nature.com/articles/s41592-020-01008-z.",
                "description": "Isensee F, Jaeger PF, Kohl SAA, et al. nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation. Nat. Methods. 2021;18(2):203–211. Available at: https://www.nature.com/articles/s41592-020-01008-z.",
                "type": "string",
                "readOnly": True,
            },
            "confirmation": {
                "title": "Accept",
                "default": False,
                "type": "boolean",
                "readOnly": False,
                "required": True,
                "description": "I will cite the publications above if applicable.",
            },
        },
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "models": {
                "title": "Model selection",
                "description": "Select one or more models to use during analysis.",
                "type": "array",
                "items": {"type": "string", "enum": ["bca", "body", "total"]},
                "default": ["bca"],
            },
            "total_models": {
                "title": "Optional models for 'total'",
                "description": "Run only if 'total' is selected.",
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "lung_vessels",
                        "cerebral_bleed",
                        "hip_implant",
                        "coronary_arteries",
                        "pleural_pericard_effusion",
                        "liver_vessels",
                    ],
                },
                "default": [],
                "readOnly": False,
            },
            "strict_mode": {
                "title": "Strict mode",
                "description": "When enabled, the workflow must produce all expected outputs. The process will fail if any required output is missing.",
                "type": "boolean",
                "default": False,
                "required": True,
                "readOnly": False,
            },
            "single_execution": {
                "title": "Single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
                "readOnly": True,
            },
            "input": {
                "title": "Input modality",
                "default": "CT",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
                "required": True,
            },
        },
    },
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=60),
}

dag = DAG(
    dag_id="body-and-organ-analysis",
    default_args=args,
    concurrency=10,
    max_active_runs=max_active_runs,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag, parallel_downloads=5, check_modality=False)

dcm2nifti = DcmConverterOperator(
    dag=dag, input_operator=get_input, output_format="nii.gz"
)

boa = BodyAndOrganAnalysisOperator(dag=dag, input_operator=dcm2nifti)

boa_check = BoaOutputCheckOperator(dag=dag, input_operator=boa)

seg2dicom = Itk2DcmSegOperator(
    dag=dag,
    segmentation_operator=boa_check,
    input_type="multi_label_seg",
    input_operator=get_input,
    skip_empty_slices=True,
    multi_label_seg_name=dag.dag_id,
    multi_label_seg_info_json="seg_info.json",
    alg_name=dag.dag_id,
    series_description=dag.dag_id,
    single_label_seg_info="from_file_name",
)

send_task = DcmSendOperator(
    dag=dag,
    input_operator=seg2dicom,
)

push_to_minio = MinioOperator(
    dag=dag,
    none_batch_input_operators=[boa],
    whitelisted_file_extensions=[".json", ".xlsx", ".pdf"],
    # whitelisted_file_extensions=[".json",".xlsx",".pdf",".nii.gz"]
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

# --- Task flow ---
get_input >> dcm2nifti >> boa >> boa_check >> seg2dicom >> send_task >> clean
boa_check >> push_to_minio >> clean
