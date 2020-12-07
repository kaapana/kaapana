from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSeg2ItkOperator import DcmSeg2ItkOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from nnunet_training.NnUnetOperator import NnUnetOperator
from nnunet_training.LocalNnUnetPrepOperator import LocalNnUnetPrepOperator


ui_forms = {
    "publication_form": {
        "type": "object",
        "properties": {
            "title": {
                "title": "Title",
                "default": "Automated Design of Deep Learning Methods\n for Biomedical Image Segmentation",
                "type": "string",
                "readOnly": True,
            },
            "authors": {
                "title": "Authors",
                "default": "Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein",
                "type": "string",
                "readOnly": True,
            },
            "link": {
                "title": "DOI",
                "default": "https://arxiv.org/abs/1904.08128",
                "description": "DOI",
                "type": "string",
                "readOnly": True,
            },
            "confirmation": {
                "title": "Accept",
                "default": False,
                "type": "boolean",
                "readOnly": True,
                "required": True,
            }
        }
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "input": {
                "title": "Input Modality",
                "default": "SEG",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
            }
        }
    }
}
args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='nnunet-train',
    default_args=args,
    concurrency=5,
    max_active_runs=2,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag, check_modality=True)
dcm2nifti_seg = DcmSeg2ItkOperator(
    dag=dag,
    input_operator=get_input,
    output_type="nii.gz",
    seg_filter="liver",
    parallel_id='seg',
)

get_ref_ct_series_from_seg = LocalGetRefSeriesOperator(dag=dag, input_operator=get_input, search_policy="reference_uid", modality=None)
dcm2nifti_ct = DcmConverterOperator(dag=dag, input_operator=get_ref_ct_series_from_seg, parallel_id='ct', output_format='nii.gz')

training_data_preparation = LocalNnUnetPrepOperator(
    dag=dag,
    training_name="liver_test",
    seg_input_operator=dcm2nifti_seg,
    dicom_input_operator=dcm2nifti_ct,
    licence="NA",
    version="NA",
    tensor_size="3D",
    shuffle_seed=None,
    test_percentage=10,
    operator_out_dir='datasets',
    file_extensions='*.nii.gz',
    copy_target_data=True,
)


# nnunet_train = NnUnetOperator(dag=dag,mode="training" input_dirs=[dcm2nifti.operator_out_dir], input_operator=dcm2nifti)
#clean = LocalWorkflowCleanerOperator(dag=dag,clean_workflow_dir=True)

get_input >> dcm2nifti_seg >> training_data_preparation
get_input >> get_ref_ct_series_from_seg >> dcm2nifti_ct >> training_data_preparation
# >> clean
