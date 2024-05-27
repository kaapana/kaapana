# -*- coding: utf-8 -*-

import os
import json
from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapanapy.Clients.OpensearchHelper import KaapanaOpensearchHelper
from kaapanapy.logger import get_logger
from multiprocessing.pool import ThreadPool
from os.path import join, exists, dirname
import shutil
import glob
import pydicom
from kaapana.operators.HelperCaching import cache_operator_output

logger = get_logger(__file__)


class LocalGetInputDataOperator(KaapanaPythonBaseOperator):
    """
    Operator to get input data for a workflow/dag.

    This operator pulls all defined files from it's defined source and stores the files in the workflow directory.
    All subsequent operators can get and process the files from within the workflow directory.
    Typically, this operator can be used as the first operator in a workflow.

    **Inputs:**

    * data_form: 'json'
    * data_type: 'dicom' or 'json'
    * dataset_limit: limit the download series list number
    * include_custom_tag_property: Key in workflow_form used to specify tags that must be present in the data for inclusion
    * exclude_custom_tag_property: Key in workflow_form used to specify tags that, if present in the data, lead to exclusion

    **Outputs:**

    * Stores downloaded 'dicoms' or 'json' files in the 'operator_out_dir'
    """

    def check_dag_modality(self, input_modality):
        config = self.conf
        input_modality = input_modality.lower()
        if (
            config is not None
            and "form_data" in config
            and config["form_data"] is not None
            and "input" in config["form_data"]
        ):
            dag_modalities = config["form_data"]["input"].lower()
            if input_modality not in dag_modalities:
                logger.error("check_dag_modality failed!")
                logger.error(
                    f"DAG modality vs input modality: {dag_modalities} vs {input_modality}"
                )
                logger.error("Wrong modality for this DAG!")
                logger.error("ABORT")
                raise ValueError("ERROR")
            else:
                logger.warning("Could not find DAG modality in DAG-run conf!")
                logger.warning("Skipping 'check_dag_modality'")
                return

    def get_data(self, series_dict):
        download_successful = True
        studyUID, seriesUID, dag_run_id = (
            series_dict["studyUID"],
            series_dict["seriesUID"],
            series_dict["dag_run_id"],
        )
        logger.info(f"Start download series: {seriesUID}")
        target_dir = os.path.join(
            self.airflow_workflow_dir,
            dag_run_id,
            self.batch_name,
            f"{seriesUID}",
            self.operator_out_dir,
        )
        logger.info(f"# Target_dir: {target_dir}")

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        if self.data_type == "dicom":
            download_successful = self.dcmweb_helper.downloadSeries(
                series_uid=seriesUID, target_dir=target_dir
            )
            if not download_successful:
                logger.warning("Could not download DICOM data!")
                download_successful = False

        elif self.data_type == "json":
            meta_data = self.os_client.get_series_metadata(
                series_instance_uid=seriesUID
            )
            json_path = join(target_dir, "metadata.json")
            with open(json_path, "w") as fp:
                json.dump(meta_data, fp, indent=4, sort_keys=True)

        elif self.data_type == "minio":
            logger.warning("Not supported yet!")
            logger.warning("abort...")
            download_successful = False

        else:
            logger.warning("unknown data-mode!")
            logger.warning("abort...")
            download_successful = False

        return download_successful, seriesUID

    def move_series(self, src_dcm_path: str, target: str):
        logger.info(
            "############################ Get input data ############################"
        )
        logger.info(f"# Moving data from {src_dcm_path} -> {target}")
        shutil.move(src=src_dcm_path, dst=target)
        logger.info(f"# Series CTP import -> OK: {target}")

    @cache_operator_output
    def start(self, ds, **kwargs):
        logger.info("# Starting module LocalGetInputDataOperator...")
        self.conf = kwargs["dag_run"].conf
        dag_run_id = kwargs["dag_run"].run_id
        if self.conf and ("seriesInstanceUID" in self.conf):
            series_uid = self.conf.get("seriesInstanceUID")
            dcm_path = join(
                "/kaapana/mounted/ctpinput", "incoming", self.conf.get("dicom_path")
            )
            logger.info(f"# Dicom-path: {dcm_path}")
            target = join(
                self.airflow_workflow_dir,
                dag_run_id,
                "batch",
                series_uid,
                self.operator_out_dir,
            )

            if not exists(target) or not any(
                fname.endswith(".dcm") for fname in os.listdir(target)
            ):
                if not os.path.isdir(dcm_path):
                    logger.error(f"Could not find dicom dir: {dcm_path}")
                    logger.error("Abort!")
                    raise ValueError("ERROR")
                else:
                    self.move_series(src_dcm_path=dcm_path, target=target)
            else:
                logger.warning("Files have already been moved -> skipping")
            return
        if self.conf and "ctpBatch" in self.conf:
            batch_folder = join(
                "/kaapana/mounted/ctpinput", "incoming", self.conf.get("dicom_path")
            )
            logger.info(f"# Batch folder: {batch_folder}")
            dcm_series_paths = [f for f in glob.glob(batch_folder + "/*")]
            for dcm_series_path in dcm_series_paths:
                dcm_file_list = glob.glob(dcm_series_path + "/*.dcm", recursive=True)
                if dcm_file_list:
                    dcm_file = pydicom.dcmread(dcm_file_list[0], force=True)
                    series_uid = dcm_file[0x0020, 0x000E].value
                    target = join(
                        self.airflow_workflow_dir,
                        dag_run_id,
                        "batch",
                        series_uid,
                        self.operator_out_dir,
                    )
                    if exists(target) and any(
                        fname.endswith(".dcm") for fname in os.listdir(target)
                    ):
                        logger.warning("Files have already been moved -> skipping")
                    else:
                        self.move_series(src_dcm_path=dcm_series_path, target=target)
            # remove parent batch folder
            if exists(batch_folder) and not os.listdir(batch_folder):
                shutil.rmtree(batch_folder)
            return

        if self.conf and "dataInputDirs" in self.conf:
            dataInputDirs = self.conf.get("dataInputDirs")
            if not isinstance(dataInputDirs, list):
                dataInputDirs = [dataInputDirs]
            for src in dataInputDirs:
                target = join(dirname(src), self.operator_out_dir)
                if src == target:
                    logger.info(f"# Data is already at out dir location -> {target}")
                else:
                    logger.info(f"# Moving data from {src} -> {target}")
                    shutil.move(src=src, dst=target)
                    logger.info("# Dag input dir correctly adjusted.")
            return

        if self.data_form is None:
            if self.conf is not None and "data_form" in self.conf:
                logger.info("Setting data_form from conf object")
                self.data_form = self.conf["data_form"]
            else:
                logger.warning(
                    "No data_form in config or object found! Data seems to be present already..."
                )
                logger.warning("Skipping...")
                return
        if "query" in self.data_form and "identifiers" in self.data_form:
            logger.error(
                "You defined 'identifiers' and a 'query', only one definition is supported!"
            )
            exit(1)
        if "query" in self.data_form:
            self.data_form["identifiers"] = self.os_client.get_query_dataset(
                self.data_form["query"], only_uids=True
            )

        logger.debug("data_form:")
        logger.debug(json.dumps(self.data_form, indent=4, sort_keys=True))

        dataset_limit = int(self.data_form.get("dataset_limit", 0))
        self.dataset_limit = dataset_limit if dataset_limit > 0 else None

        if not self.data_form["identifiers"]:
            logger.error("Issue with data form -> exit. ")
            exit(1)

        logger.debug(f"{self.include_custom_tag_property=}")
        logger.debug(f"{self.exclude_custom_tag_property=}")

        include_custom_tag = (
            self.conf["workflow_form"][self.include_custom_tag_property]
            if self.include_custom_tag_property != ""
            else ""
        )
        exclude_custom_tag = (
            self.conf["workflow_form"][self.exclude_custom_tag_property]
            if self.include_custom_tag_property != ""
            else ""
        )

        self.dcm_uid_objects = self.os_client.get_dcm_uid_objects(
            self.data_form["identifiers"],
            include_custom_tag=include_custom_tag,
            exclude_custom_tag=exclude_custom_tag,
        )

        logger.debug(f"Dataset-limit: {self.dataset_limit}")
        logger.debug("Dicom data information:")
        logger.debug(json.dumps(self.dcm_uid_objects, indent=4, sort_keys=True))

        download_list = []
        if not self.dcm_uid_objects:
            logger.error(f"No DcmUid found for {self.conf=}")
            raise AssertionError

        for dcm_uid in self.dcm_uid_objects:
            if "study-uid" not in dcm_uid:
                logger.error(f"'study-uid' not found in {dcm_uid=}")
                raise AssertionError
            if "series-uid" not in dcm_uid:
                logger.error(f"'series-uid' not found in {dcm_uid=}")
                raise AssertionError

            if "modality" in dcm_uid and self.check_modality:
                modality = dcm_uid["curated_modality"]
                self.check_dag_modality(input_modality=modality)

            study_uid = dcm_uid["study-uid"]
            series_uid = dcm_uid["series-uid"]

            download_list.append(
                {
                    "studyUID": study_uid,
                    "seriesUID": series_uid,
                    "dag_run_id": dag_run_id,
                }
            )

        logger.debug(f"SERIES FOUND: {len(download_list)}")
        logger.debug(f"SERIES LIMIT: {self.dataset_limit}")
        download_list = (
            download_list[: self.dataset_limit]
            if self.dataset_limit is not None
            else download_list
        )
        logger.debug(f"SERIES TO LOAD: {len(download_list)}")
        if len(download_list) == 0:
            logger.error(f"No series to download !! ")
            raise AssertionError
        series_download_fail = []
        self.dcmweb_helper = HelperDcmWeb(
            application_entity="KAAPANA", dag_run=kwargs["dag_run"]
        )
        with ThreadPool(self.parallel_downloads) as threadpool:
            results = threadpool.imap_unordered(self.get_data, download_list)
            for download_successful, series_uid in results:
                logger.info(f"Series download successfull: {series_uid=}")
                if not download_successful:
                    series_download_fail.append(series_uid)

            if len(series_download_fail) > 0:
                logger.error(
                    f"Some series could not be downloaded : {series_download_fail=} "
                )
                raise AssertionError

    def __init__(
        self,
        dag,
        name="get-input-data",
        data_type="dicom",
        data_form=None,
        check_modality=False,
        dataset_limit=None,
        parallel_downloads=3,
        include_custom_tag_property="",
        exclude_custom_tag_property="",
        batch_name=None,
        **kwargs,
    ):
        """
        :param data_type: 'dicom' or 'json'
        :param data_form: 'json'
        :param check_modality: 'True' or 'False'
        :param dataset_limit: limits the download list
        :param include_custom_tag_property: key in workflow_form for filtering with tags that must exist
        :param exclude_custom_tag_property: key in workflow_form for filtering with tags that must not exist
        :param parallel_downloads: default 3, number of parallel downloads
        """

        self.data_type = data_type
        self.data_form = data_form
        self.dataset_limit = dataset_limit
        self.check_modality = check_modality
        self.parallel_downloads = parallel_downloads

        self.include_custom_tag_property = include_custom_tag_property
        self.exclude_custom_tag_property = exclude_custom_tag_property

        self.os_client = KaapanaOpensearchHelper()
        super().__init__(
            dag=dag,
            name=name,
            batch_name=batch_name,
            python_callable=self.start,
            max_active_tis_per_dag=10,
            execution_timeout=timedelta(minutes=60),
            **kwargs,
        )
