from airflow.utils.dates import days_ago
from datetime import timedelta, datetime
from airflow.models import DAG
from node_metrics.LocalPushToPromOperator import LocalPushToPromOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator

max_active_runs = 5
args = {
    "ui_visible": False,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=60),
}

dag = DAG(
    dag_id="metrics-collect-central",
    default_args=args,
    concurrency=4,
    max_active_runs=1,
    schedule_interval="@hourly",
)

higher_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
lower_timestamp = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S.%f")

get_input = LocalGetInputDataOperator(
    dag=dag,
    data_form={
        "cohort_identifiers": [],
        "cohort_query": {
            "index": "meta-index",
            "query": {
                "bool": {
                    "must": [],
                    "filter": [
                        {"match_all": {}},
                        {"match_phrase": {"00080060 Modality_keyword.keyword": "OT"}},
                        {
                            "match_phrase": {
                                "00100010 PatientName_keyword_alphabetic": "node-metrics"
                            }
                        },
                        {
                            "range": {
                                "timestamp": {
                                    "gte": lower_timestamp,
                                    "lt": higher_timestamp,
                                }
                            }
                        },
                    ],
                    "should": [],
                    "must_not": [],
                }
            },
        },
    },
    check_modality=True,
)

dcm2txt = Bin2DcmOperator(
    dag=dag, input_operator=get_input, name="extract-binary", file_extensions="*.dcm"
)

push_metrics = LocalPushToPromOperator(dag=dag, input_operator=dcm2txt)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> dcm2txt >> push_metrics >> clean
