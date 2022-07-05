import glob, os, shutil
from pathlib import Path
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger
import pydicom
from datetime import timedelta


class LocalCtpQuarantineCheckOperator(KaapanaPythonBaseOperator):
    """
        Operator to check the CTP quarantine folder (FASTDATADIR/ctp/incoming/.quarantines), for dicom files.
        If files are found, trigger_dag_id is triggered.
         **Inputs:**
         Quarantine folder of the CTP
        **Outputs:**
        Found quarantine files are processed as incoming files and added to the PACs and meta.
    """
    def check(self, **kwargs):
        conf = kwargs['dag_run'].conf
        if conf and "dataInputDirs" in conf:
            print("This is already a Dag triggered by this operator")
            return
        quarantine_path = os.path.join("/ctpinput", ".quarantines")
        path_list = [p for p in Path(quarantine_path).rglob("*.dcm") if p.is_file()]
        if path_list:
            print("Files found in quarantine!")
            # limit number of handled file in the same dag run
            devided_path_list = [path_list[x:x + self.max_number_of_batch_files]
                                 for x in range(0, len(path_list), self.max_number_of_batch_files)]
            for path_list_part in devided_path_list:
                dag_run_id = generate_run_id(self.trigger_dag_id)
                print("MOVE with dag run id: ", dag_run_id)
                target_list = set()
                try:
                    for dcm_file in path_list_part:
                        series_uid = pydicom.dcmread(dcm_file, force=True)[0x0020, 0x000E].value
                        target = os.path.join("/data", dag_run_id, "batch", series_uid, self.target_dir)
                        if not os.path.exists(target):
                            os.makedirs(target)
                        print("SRC: {}".format(dcm_file))
                        print("TARGET: {}".format(target))
                        target_list.add(target)
                        shutil.move(str(dcm_file), target)
                    conf = {"dataInputDirs": list(target_list)}
                except Exception as e:
                    print("An exception occurred, when moving files:")
                    print(e)
                    print("Please have a look at this file:" + str(dcm_file))
                    print("Remove or future process unvaild file")
                    if target_list:
                        print("Trigger all already moved files.")
                        conf = {"dataInputDirs": list(target_list)}
                        trigger(dag_id=self.trigger_dag_id, run_id=dag_run_id, conf=conf, replace_microseconds=False)
                    exit(1)

                print(("TRIGGERING! DAG-ID: %s RUN_ID: %s" % (self.trigger_dag_id, dag_run_id)))
                trigger(dag_id=self.trigger_dag_id, run_id=dag_run_id, conf=conf, replace_microseconds=False)

    def __init__(self,
                 dag,
                 trigger_dag_id='service-process-incoming-dcm',
                 max_number_of_batch_files=2000,
                 target_dir="get-input-data",
                 **kwargs):
        """
        :param trigger_dag_id: Is by default "service-process-incoming-dcm", has to be set for a different incoming process.
        :param max_number_of_batch_files: default 2000, defines the maximum of files handled in a single dag trigger.
        :param target_dir: The input dir of the trigger_dag_id. Has to be set, for a different incoming process.
        """


        name = "ctp-quarantine-check"
        self.trigger_dag_id = trigger_dag_id
        self.max_number_of_batch_files = max_number_of_batch_files
        self.target_dir = target_dir

        super().__init__(
            dag=dag,
            name=name,
            python_callable=self.check,
            execution_timeout=timedelta(minutes=180),
            **kwargs)
