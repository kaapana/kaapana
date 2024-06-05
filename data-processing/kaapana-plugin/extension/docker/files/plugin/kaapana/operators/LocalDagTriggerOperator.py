from kaapana.operators.HelperMinio import HelperMinio
from kaapanapy.Clients.OpensearchHelper import KaapanaOpensearchHelper, DicomKeywords
from kaapanapy.logger import get_logger

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

from kaapana.blueprints.kaapana_utils import generate_run_id
from airflow.api.common.trigger_dag import trigger_dag as trigger
from os.path import join
import os
import time
import errno
import json
from glob import glob
import shutil
import pydicom
from datetime import timedelta

logger = get_logger(__file__)


class LocalDagTriggerOperator(KaapanaPythonBaseOperator):
    def __init__(
        self,
        dag,
        trigger_dag_id: str,
        cache_operators: list = [],
        target_bucket: str = None,
        trigger_mode: str = "single",
        wait_till_done: bool = False,
        use_dcm_files: bool = True,
        from_data_dir: bool = False,
        delay: int =10,
        **kwargs,
    ):
        """
        Trigger dag-runs based on the workflow configuration.


        :param: trigger_dag_id:
        :param: cache_operators:
        :param: target_bucket:
        :param: trigger_mode: One of ['single','batch']. In case of use_dcm_files = False: trigger_mode specifies if the series are processed in sinle or batch mode.
        :param: wait_till_done: If True, wait until all triggered dag-runs are finished.
        :param: use_dcm_files:
        :param: from_data_dir:
        :param: delay: If wait_till_done = True: Time between to checks, if all triggered dag-runs are finished.
        """
        self.trigger_dag_id = trigger_dag_id
        self.wait_till_done = wait_till_done
        self.trigger_mode = trigger_mode.lower()
        self.cache_operators = (
            cache_operators if isinstance(cache_operators, list) else [cache_operators]
        )
        self.target_bucket = target_bucket
        self.use_dcm_files = use_dcm_files
        self.from_data_dir = from_data_dir
        self.delay = delay

        name = "trigger_" + self.trigger_dag_id

        super(LocalDagTriggerOperator, self).__init__(
            dag=dag,
            name=name,
            python_callable=self.trigger_dag,
            execution_timeout=timedelta(hours=15),
            **kwargs,
        )
    
    def check_cache(self, dicom_series: dict, cache_operator) -> bool:
        """
        Download data from MinIO into an operator out directory for the series

        Return:
            False: If the output directory is empty.
            True: If output directory not empty.
        """
        loaded_from_cache = True
        series_uid = dicom_series["dcm-uid"]["series-uid"]

        output_dir = join(
            self.run_dir, self.batch_name, series_uid, self.operator_out_dir
        )

        object_dirs = [join(self.batch_name, series_uid, cache_operator)]
        minio_client = HelperMinio(dag_run=self.dag_run)
        minio_client.apply_action_to_object_dirs(
            "get",
            bucket_name=self.target_bucket,
            local_root_dir=output_dir,
            object_dirs=object_dirs,
        )
        try:
            if len(os.listdir(output_dir)) == 0:
                loaded_from_cache = False
        except FileNotFoundError:
            loaded_from_cache = False

        if loaded_from_cache:
            logger.info(f"✔ Chache data found for series: {dicom_series["dcm-uid"]["series-uid"]}")
        else:
            logger.info(f"✘ NO data found for series: {dicom_series["dcm-uid"]["series-uid"]}")

        return loaded_from_cache


    def get_dicom_list_from_input_dir(self):
        """
        Return meta information about dicom files found in the operators input directory.
        """
        batch_dir = join(self.airflow_workflow_dir, self.dag_run_id, "batch", "*")
        batch_folders = sorted([f for f in glob(batch_dir)])
        dicom_info_list = []
        logger.info("Search for DICOM files in input-dir ...")
        no_data_processed = True
        for batch_element_dir in batch_folders:
            input_dir = join(batch_element_dir, self.operator_in_dir)
            dcm_file_list = glob(input_dir + "/*.dcm", recursive=True)
            if len(dcm_file_list) == 0:
                logger.warning(f"Couldn't find any DICOM file in dir: {input_dir=}")
                continue
            no_data_processed = False
            dicom_file = pydicom.dcmread(dcm_file_list[0])
            if self.from_data_dir:
                dicom_info_list.append(
                    {"input-dir": input_dir, "series-uid": dicom_file[0x0020, 0x000E].value}
                )
            else:
                dicom_info_list.append(
                    {
                        "dcm-uid": {
                            "study-uid": dicom_file[0x0020, 0x000D].value,
                            "series-uid": dicom_file[0x0020, 0x000E].value,
                            "modality": dicom_file[0x0008, 0x0060].value,
                        }
                    }
                )
        if no_data_processed:
            logger.error("No files processed in any batch folder!")
            raise AssertionError

        return dicom_info_list

    def get_dicom_list_from_dag_configuration(self):
        """
        Return meta information about series specified in the dag configuration.
        """
        dicom_info_list = []
        os_client = KaapanaOpensearchHelper()
        logger.info("Using DAG-conf for series ...")
        if self.conf == None or not "inputs" in self.conf:
            logger.error("No config or inputs in config found!")
            raise AssertionError

        dataset_limit = self.conf["dataset_limit"]
        inputs = self.conf["inputs"]
        if not isinstance(inputs, list):
            inputs = [inputs]

        for input in inputs:
            if "opensearch-query" in input:
                opensearch_query = input["opensearch-query"]
                if "query" not in opensearch_query:
                    logger.error(
                        f"'query' not found in 'opensearch-query': {input=}"
                    )
                    raise AssertionError
                if "index" not in opensearch_query:
                    logger.error(
                        f"'index' not found in 'opensearch-query': {input=}"
                    )
                    raise AssertionError

                query = opensearch_query["query"]

                dataset = os_client.get_query_dataset(query=query)
                logger.debug(f"opensearch-query: found {len(dataset)} results.")
                if dataset_limit is not None:
                    logger.debug(f"Limiting dataset to: {dataset_limit}")
                    dataset = dataset[:dataset_limit]
                for series in dataset:
                    series = series["_source"]
                    dicom_info_list.append(
                        {
                            "dcm-uid": {
                                "study-uid": series[DicomKeywords.study_uid_tag],
                                "series-uid": series[DicomKeywords.series_uid_tag],
                                "modality": series[DicomKeywords.modality_tag],
                            }
                        }
                    )

            elif "dcm-uid" in input:
                dcm_uid = input["dcm-uid"]

                if "study-uid" not in dcm_uid:
                    logger.error(f"'study-uid' not found in 'dcm-uid': {input=}")
                    raise ValueError("study-uid not found")
                if "series-uid" not in dcm_uid:
                    logger.error(f"'series-uid' not found in 'dcm-uid': {input=}")
                    raise ValueError("study-uid not found")

                dicom_info_list.append(
                    {
                        "dcm-uid": {
                            "study-uid": dcm_uid["study-uid"],
                            "series-uid": dcm_uid["series-uid"],
                            "modality": dcm_uid["modality"],
                        }
                    }
                )

            else:
                logger.error("Error with dag-config!")
                logger.error(f"Unknown input: {input=}")
                logger.error("Supported 'dcm-uid' and 'opensearch-query' ")
                logger.error(f"Dag-conf: {self.conf=}")
                raise ValueError("Error with dag-config!")
        return dicom_info_list

    def get_dicom_list(self):
        """
        Return a list of meta information about dicom series.
        
        If self.use_dcm_files is True: Collect series from operator directory
        Else: Collect series from dag config.

        All objects in the returned list are in one of these formats
        Either:
        {
            "dcm-uid": {
                "study-uid": study_uid,
                "series-uid": series_uid,
                "modality": modality,
            }
        }
        or
        { "input-dir": input_dir, "series-uid": series_uid }
        """

        logger.info(" Get DICOM list ...")
        if self.use_dcm_files:
            return self.get_dicom_list_from_input_dir()
            
        else:
            return self.get_dicom_list_from_dag_configuration()

    def copy(self, src, target):
        logger.debug(f"Copy from {src=} to {target=}")
        try:
            shutil.copytree(src, target)
        except OSError as e:
            # If the error was caused because the source wasn't a directory
            if e.errno == errno.ENOTDIR:
                shutil.copy(src, target)
            else:
                logger.error(f"Directory not copied.")
                raise Exception("Directory not copied. Error: %s" % e)

    def trigger_dag_dicom_helper(self):
        """
        Triggers Airflow workflows passed with the input DICOM data.

        Returns:
            pending_dags (list): List containing information about triggered DAGs that are still pending.
        """
        pending_dags = []
        dicom_info_list = self.get_dicom_list()
        logger.info(f"DICOM-LIST: {dicom_info_list}")
        trigger_series_list = []
        for dicom_series in dicom_info_list:
            if self.trigger_mode == "batch":
                if len(trigger_series_list) == 0:
                    trigger_series_list.append([])
                trigger_series_list[0].append(dicom_series)
            elif self.trigger_mode == "single":
                trigger_series_list.append([dicom_series])
            else:
                logger.error(f"TRIGGER_MODE: {self.trigger_mode} is not supported!")
                logger.error(f"Please use: 'single' or 'batch' -> abort.")
                raise ValueError("TRIGGER_MODE not supported")

        logger.info("TRIGGER-LIST: ")
        logger.info(json.dumps(trigger_series_list, indent=4, sort_keys=True))

        # trigger current workflow data
        if self.use_dcm_files and self.from_data_dir:
            dag_run_id = generate_run_id(self.trigger_dag_id)
            target_list = set()
            for dicom_series in dicom_info_list:
                src = dicom_series["input-dir"]
                target_dir = (
                    self.operator_out_dir if self.operator_out_dir else "get-input-data"
                )
                target = join(
                    self.airflow_workflow_dir,
                    dag_run_id,
                    self.batch_name,
                    dicom_series["series-uid"],
                    target_dir,
                )
                target_list.add(target)
                self.copy(src, target)
            self.conf["dataInputDirs"] = list(target_list)
            trigger(
                dag_id=self.trigger_dag_id,
                run_id=dag_run_id,
                conf=self.conf,
                replace_microseconds=False,
            )

        for element in trigger_series_list:
            self_conf_copy = self.conf.copy()
            if "inputs" in self_conf_copy:
                del self_conf_copy["inputs"]
            conf = {
                **self_conf_copy,
                "inputs": element,
                # "conf": self.conf
            }
            dag_run_id = generate_run_id(self.trigger_dag_id)
            triggered_dag = trigger(
                dag_id=self.trigger_dag_id,
                run_id=dag_run_id,
                conf=conf,
                replace_microseconds=False,
            )
            pending_dags.append(triggered_dag)

        return pending_dags



    def check_if_data_arrived(self, pending_dag):
        """
        Verify that all inputs of a dag-run exist in the cache_operator directories.

        :param: pending_dag: DAG
        
        Return: None

        Raises:
            ValueError: If some data cannot be found in the 
        """
        for series in pending_dag.conf["inputs"]:
            for cache_operator in self.cache_operators:
                if not self.check_cache(
                    dicom_series=series, cache_operator=cache_operator
                ):
                    logger.error("Could still not find the data after the sub-dag.")
                    raise ValueError("Data not found")

    def trigger_dag(self, ds, **kwargs):
        """
        Orchestrates triggering of Airflow workflows.

        Parameters:
            ds (str): Datestamp parameter for Airflow.
            kwargs: Additional keyword arguments, including `dag_run` information.

        Returns:
            None

        Raises:
            ValueError: If any triggered DAG fails or encounters unexpected behavior.
        """
        pending_dags = []
        self.dag_run = kwargs["dag_run"]
        self.conf = kwargs["dag_run"].conf
        self.dag_run_id = kwargs["dag_run"].run_id

        if self.trigger_dag_id == "":
            logger.info(
                f"trigger_dag_id is empty, setting to {self.conf['workflow_form']['trigger_dag_id']}"
            )
            self.trigger_dag_id = self.conf["workflow_form"]["trigger_dag_id"]

        logger.debug(f"{self.use_dcm_files=}")
        logger.debug(f"{self.dag_run_id=}")
        logger.debug(f"{self.trigger_dag_id=}")

        if not self.use_dcm_files:
            logger.info("just running the dag without moving any dicom files beforehand")
            dag_run_id = generate_run_id(self.trigger_dag_id)
            triggered_dag = trigger(
                dag_id=self.trigger_dag_id,
                run_id=dag_run_id,
                conf=self.conf,
                replace_microseconds=False,
            )
            pending_dags.append(triggered_dag)
        else:
            pending_dags = self.trigger_dag_dicom_helper()

        if self.wait_till_done:
            self.wait_for_pending_dag_runs(pending_dag_runs=pending_dags)

        logger.info("#######################  DONE  ##############################")


    def wait_for_pending_dag_runs(self, pending_dag_runs: list):
        """
        Wait until all triggered dag-runs have completed.

        :param: pending_dag_runs: List of dag-runs to watch

        Raises:
            ValueError if dag-run in state 'failed' or unknown state.

        Return None
        """
        succeeded_dag_runs = []
        while len(pending_dag_runs) > 0:
            logger.info(f"Some triggered DAGs are still pending -> waiting {self.delay} s")
            for pending_dag in list(pending_dag_runs):
                pending_dag.update_state()
                state = pending_dag.get_state()
                logger.debug(f"{pending_dag=} , {state=}")
                if state == "running":
                    continue
                elif state == "success":
                    succeeded_dag_runs.append(pending_dag)
                    pending_dag_runs.remove(pending_dag)
                    # keep the same functionality if triggering with dicom
                    if self.use_dcm_files:
                        self.check_if_data_arrived(pending_dag=pending_dag)

                elif state == "failed":
                    logger.error(f"Dag run {pending_dag.id=} failed")
                    raise ValueError(f"Dag run {pending_dag.id=} with {state=}")
                else:
                    logger.error("Unknown state!")
                    raise ValueError(f"Dag-run {pending_dag.id=} has unknown {state=}")

            time.sleep(self.delay)