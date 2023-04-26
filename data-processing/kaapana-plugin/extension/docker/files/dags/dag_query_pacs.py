from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmQueryOperator import DcmQueryOperator
from kaapana.operators.LocalJson2MetaOperator import LocalJson2MetaOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from airflow.operators.python import PythonOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


log = LoggingMixin().log

ae_title = "NONE"
pacs_host = ""
pacs_port = 11112
local_ae_title = "KAAPANAQR"
start_date = ""
end_date = ""
level = "series"
max_query_size = ""

ui_forms = {
    "data_form": {},
    "workflow_form": {
        "type": "object",
        "properties": {
            "pacs_host": {
                "title": "Remote host",
                "description": "Specify the url/IP of the PACS to query.",
                "type": "string",
                "default": pacs_host,
                "required": True
            },
            "pacs_port": {
                "title": "Remote port",
                "description": "Specify the port of the PACS to query.",
                "type": "integer",
                "default": pacs_port,
                "required": True
            },
            "ae_title": {
                "title": "Remote AE-title",
                "description": "Specify the AE-title of the PACS to query.",
                "type": "string",
                "default": ae_title,
                "required": True
            },
            "local_ae_title": {
                "title": "Local AE-title",
                "description": "Specify the local AE-title used.",
                "type": "string",
                "default": local_ae_title,
                "required": True
            },
            "start_date": {
                "title": "Start Date",
                "description": "The first date in query (empty if open begin)",
                "type": "string",
                "default": start_date,
                "required": False
            },
            "end_date": {
                "title": "End Date",
                "description": "The latest date in query (empty if open end)",
                "type": "string",
                "default": end_date,
                "required": False
            },
            "level": {
                "title": "Level",
                "description": "Specify the Level of the quer (e.g. series, study)",
                "type": "string",
                "default": level,
                "required": True
            },
            "max_query_size": {
                "title": "Max Query Size",
                "description": "The wanted maximum size of a individual query.",
                "type": "string",
                "default": max_query_size,
                "required": False
            },
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


args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}


class Dcm2MetaJsonLinesOperator(KaapanaPythonBaseOperator):
    def dcm2meta_json_func(self, ds, **kwargs):
        import json
        import os
        import glob
        from kaapana.operators.Dcm2MetaJsonConverter import Dcm2MetaJsonConverter

        for prerequisit in ["ae_title", "pacs_host", "pacs_port", "local_ae_title", "ti", "dag_run", "input_operator"]:
            if prerequisit not in kwargs:
                raise Exception(f"Prerequisite {prerequisit} is not in environment. (kwargs: {kwargs})")

        converter = Dcm2MetaJsonConverter()
        #operator_in = "dcmqr"
        # use task id as output
        operator_out = kwargs['ti'].task_id 
        run_dir = os.path.join(self.airflow_workflow_dir, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, '*'))]
        for batch_element_dir in batch_folder:
            jsonl_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.jsonl"), recursive=True))
            print(f"Processing batch {batch_element_dir} - found {len(jsonl_files)} inputs")
            for jsonl_file in jsonl_files:
                out_path = jsonl_file.replace(self.operator_in_dir, operator_out)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w") as outfile:
                    with open(jsonl_file, 'r') as infile:
                        for line in infile:
                            dcm_json_data = json.loads(line)
                            meta_json_data = converter.dcmJson2metaJson(dcm_json_data)
                            meta_json_data["from_ae_title"] = kwargs["ae_title"]
                            meta_json_data["from_pacs_host"] = kwargs["pacs_host"]
                            meta_json_data["from_pacs_port"] = kwargs["pacs_port"]
                            meta_json_data["local_ae_title"] = kwargs["local_ae_title"]
                            json.dump(meta_json_data, outfile)
                            outfile.write("\n")

    def __init__(self,
                 dag,
                 ae_title,
                 local_ae_title,
                 pacs_host,
                 pacs_port,
                 **kwargs):
        
        super().__init__(
            dag=dag,
            name="dcm_json2meta_json",
            python_callable=self.dcm2meta_json_func,
            **kwargs
        )




dag = DAG(
    dag_id='query-pacs',
    default_args=args,
    concurrency=1,
    max_active_runs=10,
    schedule_interval=None
)


dcm_query = DcmQueryOperator(
    dag=dag,
    ae_title=ae_title,
    local_ae_title=local_ae_title,
    pacs_host=pacs_host,
    pacs_port=pacs_port,
    start_date=start_date,
    end_date=end_date,
    level=level,
    max_query_size= max_query_size
)

dcm2meta_json = Dcm2MetaJsonLinesOperator(
    dag=dag,
    input_operator=dcm_query,
    ae_title=ae_title,
    local_ae_title=local_ae_title,
    pacs_host=pacs_host,
    pacs_port=pacs_port
)

push_jsonl = LocalJson2MetaOperator(
     dag=dag,
     input_operator=dcm2meta_json,
     jsonl_operator=dcm2meta_json,
     check_in_pacs=False,
     #opensearch_index="query-metaindex"
)


clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=False)


dcm_query >> dcm2meta_json >> push_jsonl >> clean