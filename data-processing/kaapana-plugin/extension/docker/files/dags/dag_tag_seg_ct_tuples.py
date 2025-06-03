from datetime import datetime, timedelta

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.GetRefSeriesOperator import GetRefSeriesOperator
from kaapana.operators.LocalTaggingOperator import LocalTaggingOperator
from airflow.utils.dates import days_ago
from airflow.models import DAG


ui_forms = {
    "documentation_form": {
        "path": "/user_guide/system/airflow.html#tag-seg-ct-tuples",
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "action": {
                "title": "Action",
                "description": "Choose if you want to add/delete tags",
                "enum": ["add", "delete"],
                "type": "string",
                "default": "add",
                "required": True,
                "readOnly": False,
            },
            "tags": {
                "title": "Tags",
                "description": "Specify a , seperated list of tags to add/delete (e.g. tag1,tag2)",
                "type": "string",
                "default": "",
                "required": True,
            },
            "input": {
                "title": "Input",
                "default": "SEG,RTSTRUCT",
                "description": "Input-data modality",
                "type": "string",
                "readOnly": True,
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
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
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="tag-seg-ct-tuples",
    default_args=args,
    concurrency=10,
    max_active_runs=1,
    schedule_interval=None,
)

get_input_dicom = GetInputOperator(
    dag=dag, name="get-input-dicom", check_modality=True, parallel_downloads=5
)

get_input_json = GetInputOperator(
    dag=dag,
    name="get-input-json",
    check_modality=True,
    data_type="json",
    parallel_downloads=5,
)

get_ref_ct_series_from_seg = GetRefSeriesOperator(
    dag=dag,
    input_operator=get_input_dicom,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
    data_type="json",
)

tag_cts = LocalTaggingOperator(
    dag=dag, name="tag-cts", input_operator=get_ref_ct_series_from_seg
)
tag_segs = LocalTaggingOperator(dag=dag, name="tag-segs", input_operator=get_input_json)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input_dicom >> get_ref_ct_series_from_seg >> tag_cts
get_input_json >> tag_segs >> clean
tag_cts >> clean
