from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSeg2ItkOperator import DcmSeg2ItkOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator

from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from radiomics.RadiomicsOperator import RadiomicsOperator

from avid_operator.AVIDBaseOperator import AVIDBaseOperator
from avid.actions.MitkFileConverter import MitkFileConverterBatchAction
from avid.actions.genericCLIAction import GenericCLIAction
from avid.linkers import KeyValueLinker
from kaapana.operators.KaapanaBaseOperator import default_registry, kaapana_build_version
from avid.actions.MitkCLGlobalImageFeatures import MitkCLGlobalImageFeaturesBatchAction as RadiomicsBatchAction
from avid_operator.HelperAvid import PROP_BATCH_ID


log = LoggingMixin().log

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
                "readOnly": False,
            },
            "input": {
                "title": "Input",
                "default": "SEG",
                "description": "Input-data modality",
                "type": "string",
                "readOnly": True,
            },
            "simple-execution.splitter.input.type": {
                "title": "Input splitter",
                "default": "All",
                "description": "Splitter used for the primary inputs.",
                "type": "string",
                "enum": ["All", "Single", "Custom"],
                "readOnly": False,
            },
            "simple-execution.splitter.input.values": {
                "title": "Input splitter",
                "default": "",
                "description": "Splitter used for the primary inputs.",
                "type": "string",
                "enum": ["All", "Single", "Custom"],
                "readOnly": False,
            },
            "parameters": {
                "title": "Parameter",
                "default": "-fo 1 -cooc 1",
                "description": "Parameter for MitkCLGlobalImageFeatures.",
                "type": "string",
                "readOnly": False,
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
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='example_form',
    default_args=args,
    schedule_interval=None,
    concurrency=30,
    max_active_runs=15
)

get_input = LocalGetInputDataOperator(dag=dag, check_modality=True)
action = AVIDBaseOperator(dag=dag, input_operator=get_input, name='simple-execution',
                        executable_url='python3 /kaapanasrc/start.py',
                        image=f"{default_registry}/simple-execution:{kaapana_build_version}",
                        action_class=GenericCLIAction,
                        action_kwargs={"additionalArgs":{"test":None, "test2":None}})

put_to_minio = LocalMinioOperator(dag=dag, action='put', action_operators=[action])
get_input >> action >> put_to_minio #>> clean
