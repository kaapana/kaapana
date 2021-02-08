import glob, os, shutil
from pathlib import Path
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger

class LocalCtpQuarantineCheckOperator(KaapanaPythonBaseOperator):

    def check(self, **kwargs):
        quarantine_path = os.path.join("/ctpinput", ".quarantines")
        path_list = {p for p in Path(quarantine_path).rglob("*.dcm") if p.is_file()}
        if path_list:
                dag_run_id = generate_run_id(self.trigger_dag_id)
                series_uid = kwargs['dag_run'].conf.get('seriesInstanceUID')
                target = os.path.join("/data", dag_run_id, "batch", series_uid, self.operator_in_dir)

                if not os.path.exists(target):
                    os.makedirs(target)
                print("MOVE!")
                for dcm_file in path_list:
                    print("SRC: {}".format(dcm_file))
                    print("TARGET: {}".format(target))
                    shutil.move(str(dcm_file), target)

                print(("TRIGGERING! DAG-ID: %s RUN_ID: %s" % (self.trigger_dag_id, dag_run_id)))
                trigger(dag_id=self.trigger_dag_id, run_id=dag_run_id, replace_microseconds=False)



    def __init__(self,
                 dag,
                 trigger_dag_id='save_to_platform',
                 *args, **kwargs):

        name = "ctp-quarantine-check"
        self.trigger_dag_id = trigger_dag_id

        super().__init__(
            dag=dag,
            name=name,
            python_callable=self.check,
            * args,
            **kwargs)
