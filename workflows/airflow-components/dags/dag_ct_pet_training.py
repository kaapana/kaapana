from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime

from ct_pet_prediction.LocalDagTriggerOperator import LocalDagTriggerOperator
from ct_pet_prediction.LocalDatasetSplitOperator import LocalDatasetSplitOperator
from ct_pet_prediction.CtPetPredictionTrainingOperator import CtPetPredictionTrainingOperator

# from kaapana.operators.LocalWorkflowCleaner import LocalWorkflowCleaner

# log GPU:
# nvidia-smi -l 10 -i 0 --query-gpu=memory.used --format=csv >> gpu_log.txt

log = LoggingMixin().log

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "input": {
                "title": "Input",
                "default": "PET",
                "description": "Input-data modality",
                "type": "string",
                "readOnly": True,
            },
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
    dag_id='ct-pet-train',
    default_args=args,
    max_active_runs=2,
    # concurrency=15,
    schedule_interval=None)

timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

trigger_preprocessing = LocalDagTriggerOperator(dag=dag,
                                                trigger_dag_id='ct-pet-prep',
                                                cache_operator="normalization",
                                                target_bucket="ctpet-prep",
                                                trigger_mode="single",
                                                wait_till_done=True,
                                                use_dcm_files=False
                                                )

dataset_split = LocalDatasetSplitOperator(
    dag=dag,
    input_operator=trigger_preprocessing,
    train_percentage=80,
    test_percentage=10,
    validation_percentage=10,
    shuffle_seed=None,
    file_extensions='*.npy',
    keep_dir_structure=False,
    copy_target_data=False
)

training = CtPetPredictionTrainingOperator(
    dag=dag,
    input_operator=dataset_split,
    lr=0.0003,
    batch_size=2,
    dropout=0.25,
    epochs=50,
    cpu_count=8,
    device='cuda:0',
    model='UNet3d',
    patch_size=(96, 96, 96),
    patience=15,
    resume='',
    channels='1',
    tb_info='',
)
trigger_preprocessing >> dataset_split >> training 
