from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSeg2ItkOperator import DcmSeg2ItkOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalJson2MetaOperator import LocalJson2MetaOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalConcatJsonOperator import LocalConcatJsonOperator
from radiomics.RadiomicsOperator import RadiomicsOperator

from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log

args = {
    'ui_visible': True,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 1,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='radiomics-dcmseg',
    default_args=args,
    schedule_interval=None)

get_input = LocalGetInputDataOperator(dag=dag)
dcmseg2nrrd = DcmSeg2ItkOperator(dag=dag)
get_dicom = LocalGetRefSeriesOperator(dag=dag, from_to='segct')
dcm2nrrd = DcmConverterOperator(dag=dag, input_operator=get_dicom, output_format='nrrd')
radiomics = RadiomicsOperator(dag=dag, mask_operator=dcmseg2nrrd, input_operator=dcm2nrrd)
concat_radiomics = LocalConcatJsonOperator(dag=dag, name='concatenated-radiomics', input_operator=radiomics)
put_radiomics_to_minio = LocalMinioOperator(dag=dag, action='put', action_operators=[concat_radiomics], file_white_tuples=('.json', '.csv'))
clean = LocalWorkflowCleanerOperator(dag=dag)


get_input >> dcmseg2nrrd >> radiomics
get_input >> get_dicom >> dcm2nrrd >> radiomics >> concat_radiomics >> put_radiomics_to_minio >> clean
