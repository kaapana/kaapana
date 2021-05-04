import glob, os, shutil
from pathlib import Path
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger
import pydicom
from datetime import timedelta

class LocalCtpQuarantineCheckOperator(KaapanaPythonBaseOperator):

    def check(self, **kwargs):
        quarantine_path = os.path.join("/ctpinput", ".quarantines")
        path_list = [p for p in Path(quarantine_path).rglob("*.dcm") if p.is_file()]
        if path_list:
                # limit number of handled file in the same dag run
                devided_path_list = [path_list[x:x + self.max_number_of_batch_files]
                                     for x in range(0, len(path_list), self.max_number_of_batch_files)]
                for path_list_part in devided_path_list:
                    dag_run_id = generate_run_id(self.trigger_dag_id)
                    print("MOVE with dag run id: ", dag_run_id)
                    try:
                        for dcm_file in path_list_part:
                            series_uid = pydicom.dcmread(dcm_file)[0x0020, 0x000E].value
                            target = os.path.join("/data", dag_run_id, "batch", series_uid, 'get-input-data')
                            if not os.path.exists(target):
                                os.makedirs(target)
                            print("SRC: {}".format(dcm_file))
                            print("TARGET: {}".format(target))
                            shutil.move(str(dcm_file), target)
                    except Exception as e:
                        print(e)
                        print("An exception occurred, when moving files, trigger at least already moved files")
                        trigger(dag_id=self.trigger_dag_id, run_id=dag_run_id, replace_microseconds=False)
                        exit(1)

                    print(("TRIGGERING! DAG-ID: %s RUN_ID: %s" % (self.trigger_dag_id, dag_run_id)))
                    trigger(dag_id=self.trigger_dag_id, run_id=dag_run_id, replace_microseconds=False)


    def __init__(self,
                 dag,
                 trigger_dag_id='service-extract-metadata',
                 max_number_of_batch_files=4000,
                 *args, **kwargs):

        name = "ctp-quarantine-check"
        self.trigger_dag_id = trigger_dag_id
        self.max_number_of_batch_files = max_number_of_batch_files

        super().__init__(
            dag=dag,
            name=name,
            python_callable=self.check,
            execution_timeout=timedelta(minutes=180),
            *args,
            **kwargs)
