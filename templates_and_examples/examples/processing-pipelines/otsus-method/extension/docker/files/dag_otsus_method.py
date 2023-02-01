from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from otsus_method.OtsusMethodOperator import OtsusMethodOperator
from otsus_method.OtsusNotebookOperator import OtsusNotebookOperator


ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            }
        }
    }
}

log = LoggingMixin().log

args = {
    'ui_forms': ui_forms,
    'ui_visible': True,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='otsus-method',
    default_args=args,
    schedule_interval=None
    )



get_input = LocalGetInputDataOperator(dag=dag)

convert = DcmConverterOperator(dag=dag, input_operator=get_input)

otsus_method = OtsusMethodOperator(dag=dag,
    input_operator=convert,
    # dev_server='code-server'
    )

seg_to_dcm = Itk2DcmSegOperator(dag=dag,
    segmentation_operator=otsus_method,
    single_label_seg_info="abdomen",
    input_operator=get_input,
    series_description="Otsu's method"
)

dcm_send = DcmSendOperator(dag=dag, input_operator=seg_to_dcm)

generate_report = OtsusNotebookOperator(
    dag=dag,
    name='generate-otsus-report',
    input_operator=otsus_method,
    # dev_server='jupyterlab',
    cmds=["/bin/bash"],
    arguments=["/kaapanasrc/otsus_notebooks/run_generate_nnunet_report.sh"]
)

put_report_to_minio = LocalMinioOperator(dag=dag,
    name='upload-to-staticwebsite',
    bucket_name='staticwebsiteresults',
    action='put',
    action_operators=[generate_report],
    file_white_tuples=('.html', '.pdf')
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> convert >> otsus_method

otsus_method >> seg_to_dcm >> dcm_send >> clean
otsus_method >> generate_report >> put_report_to_minio >> clean