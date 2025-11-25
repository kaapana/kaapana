import os
from pathlib import Path
import glob
import shutil
from airflow.models import DAG
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from totalsegmentatorv2.TotalSegmentatorV2Operator import TotalSegmentatorV2Operator
from kaapana.operators.MinioOperator import MinioOperator
from kaapana.operators.UpdateSegInfoJSONOperator import UpdateSegInfoJSONOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from pyradiomics.PyRadiomicsOperator import PyRadiomicsOperator

max_active_runs = 10
concurrency = max_active_runs * 3
alg_name = "TotalSegmentator-v2"

dag = DAG(
    dag_id="total-segmentator-v2-subtask",
    concurrency=concurrency,
    max_active_runs=max_active_runs,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag, parallel_downloads=5, check_modality=True, data_type ='all')

def move_metadata_json(ds, **kwargs):
    batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
    batch_folder = [f for f in glob.glob(os.path.join(batch_dir, "*"))]
    for batch_element_dir in batch_folder:
        json_dir = Path(batch_element_dir) / get_input.operator_out_dir
        dest_dir = Path(batch_element_dir) / dcm2nifti.operator_out_dir
        json_files = [f for f in json_dir.glob("*.json")]
        print('from callback:', json_files)
        shutil.copy(json_files[0], dest_dir)

put_metadata_json = KaapanaPythonBaseOperator(
    name="put_metajson",
    python_callable=move_metadata_json,
    dag=dag,
)
  
dcm2nifti = DcmConverterOperator(
    dag=dag,
    input_operator=get_input,
    output_format="nii.gz",
)

ta = "subtask"
total_segmentator_subtask = TotalSegmentatorV2Operator(
    dag=dag,
    input_operator=dcm2nifti,
    delete_output_on_start=False,
    parallel_id=ta,
)

combine_masks_subtask = UpdateSegInfoJSONOperator(
    dag=dag,
    input_operator=total_segmentator_subtask,
    parallel_id=ta,
    mode='update_json'
)

nrrd2dcmSeg_multi_subtask = Itk2DcmSegOperator(
    dag=dag,
    input_operator=get_input,
    segmentation_operator=combine_masks_subtask,
    input_type="multi_label_seg",
    multi_label_seg_name=alg_name,
    multi_label_seg_info_json="seg_info.json",
    skip_empty_slices=True,
    parallel_id=ta,
    alg_name=f"{alg_name}-{ta}",
)

dcmseg_send_subtask = DcmSendOperator(
    dag=dag,
    input_operator=nrrd2dcmSeg_multi_subtask,
    parallel_id=ta,
)

pyradiomics_subtask = PyRadiomicsOperator(
    dag=dag,
    input_operator=dcm2nifti,
    segmentation_operator=total_segmentator_subtask,
    parallel_id=ta,
)

put_to_minio_subtask = MinioOperator(
    dag=dag,
    action="put",
    minio_prefix="radiomics-totalsegmentator-v2",
    batch_input_operators=[pyradiomics_subtask],
    whitelisted_file_extensions=[".json"],
    trigger_rule="none_failed_min_one_success",
)

clean_subtask = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
    trigger_rule="none_failed",
)

(
    get_input
    >> dcm2nifti
    >> put_metadata_json
    >> total_segmentator_subtask
    >> combine_masks_subtask
    >> nrrd2dcmSeg_multi_subtask
    >> dcmseg_send_subtask
    >> clean_subtask
)
total_segmentator_subtask >> pyradiomics_subtask >> put_to_minio_subtask
