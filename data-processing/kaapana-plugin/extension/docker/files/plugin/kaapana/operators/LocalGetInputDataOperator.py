# -*- coding: utf-8 -*-

import os
import json
from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.HelperOpensearch import HelperOpensearch
from multiprocessing.pool import ThreadPool
from os.path import join, exists, dirname
import shutil
import glob
import pydicom
from kaapana.operators.HelperCaching import cache_operator_output
import logging
import time

logging.basicConfig(level=logging.INFO)


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
                raise Exception(
                    "check_dag_modality failed! Wrong modality for this DAG! ABORT. DAG modality vs input modality: {} vs {}".format(
                        dag_modalities, input_modality
                    )
                )
            else:
                logging.warning("Could not find DAG modality in DAG-run conf!")
                logging.warning("Skipping 'check_dag_modality'")
                return

    def get_data(self, series_dict):
        download_successful = True
        studyUID, seriesUID, dag_run_id = (
            series_dict["studyUID"],
            series_dict["seriesUID"],
            series_dict["dag_run_id"],
        )

        target_dir = os.path.join(
            self.airflow_workflow_dir,
            dag_run_id,
            self.batch_name,
            f"{seriesUID}",
            self.operator_out_dir,
        )

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        if self.data_type == "dicom":
            download_successful = self.dcmweb_helper.download_series(
                study_uid=studyUID, series_uid=seriesUID, target_dir=target_dir
            )
            if not download_successful:
                download_successful = False

        elif self.data_type == "json":
            meta_data = HelperOpensearch.get_series_metadata(
                series_instance_uid=seriesUID
            )
            json_path = join(target_dir, "metadata.json")
            with open(json_path, "w") as fp:
                json.dump(meta_data, fp, indent=4, sort_keys=True)

        elif self.data_type == "minio":
            logging.error("Not supported yet!")
            logging.error("abort...")
            download_successful = False

        else:
            logging.error("unknown data-mode!")
            logging.error("abort...")
            download_successful = False

        return download_successful, seriesUID

    def move_series(self, src_dcm_path: str, target: str):
        logging.info("#")
        logging.info(
            "############################ Get input data ############################"
        )
        logging.info("#")
        logging.info(f"# Moving data from {src_dcm_path} -> {target}")
        logging.info("#")
        shutil.move(src=src_dcm_path, dst=target)
        logging.info(f"# Series CTP import -> OK: {target}")

    @cache_operator_output
    def start(self, ds, **kwargs):
        logging.info("# Starting module LocalGetInputDataOperator...")
        logging.info("#")
        self.conf = kwargs["dag_run"].conf
        dag_run_id = kwargs["dag_run"].run_id
        if self.conf and ("seriesInstanceUID" in self.conf):
            series_uid = self.conf.get("seriesInstanceUID")
            dcm_path = join(
                "/kaapana/mounted/ctpinput", "incoming", self.conf.get("dicom_path")
            )
            logging.info("#")
            logging.info(f"# Dicom-path: {dcm_path}")
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
                    raise Exception("Could not find dicom dir: {}".format(dcm_path))
                else:
                    self.move_series(src_dcm_path=dcm_path, target=target)
            else:
                logging.warning("Files have already been moved -> skipping")
            return
        if self.conf and "ctpBatch" in self.conf:
            batch_folder = join(
                "/kaapana/mounted/ctpinput", "incoming", self.conf.get("dicom_path")
            )
            logging.info(f"# Batch folder: {batch_folder}")
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
                        logging.warning("Files have already been moved -> skipping")
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
                    logging.info("#")
                    logging.info(f"# Data is already at out dir location -> {target}")
                    logging.info("#")
                else:
                    logging.info("#")
                    logging.info(f"# Moving data from {src} -> {target}")
                    logging.info("#")
                    shutil.move(src=src, dst=target)
                    logging.info("# Dag input dir correctly adjusted.")
            return

        if self.data_form is None:
            if self.conf is not None and "data_form" in self.conf:
                logging.info("Setting data_from from conf object")
                self.data_form = self.conf["data_form"]
            else:
                logging.info(
                    "No data_form in config or object found! Data seems to be present already..."
                )
                logging.info("Skipping...")
                return
        if "query" in self.data_form and "identifiers" in self.data_form:
            raise Exception(
                "You defined 'identifiers' and a 'query', only one definition is supported!"
            )
        if "query" in self.data_form:
            logging.info(
                HelperOpensearch.get_query_dataset(
                    self.data_form["query"], only_uids=True
                )
            )
            self.data_form["identifiers"] = HelperOpensearch.get_query_dataset(
                self.data_form["query"], only_uids=True
            )

        logging.info("# data_form:")
        logging.info("#")
        logging.info(json.dumps(self.data_form, indent=4, sort_keys=True))
        logging.info("#")
        logging.info("#")

        dataset_limit = int(self.data_form.get("dataset_limit", 0))
        self.dataset_limit = dataset_limit if dataset_limit > 0 else None

        if len(self.data_form["identifiers"]) > 0:
            logging.info(
                f"{self.include_custom_tag_property=}, {self.exclude_custom_tag_property=}"
            )
            include_custom_tag = ""
            exclude_custom_tag = ""
            if self.include_custom_tag_property != "":
                include_custom_tag = self.conf["workflow_form"][
                    self.include_custom_tag_property
                ]
            if self.exclude_custom_tag_property != "":
                exclude_custom_tag = self.conf["workflow_form"][
                    self.exclude_custom_tag_property
                ]
            self.dicom_data_infos = HelperOpensearch.get_dcm_uid_objects(
                self.data_form["identifiers"],
                include_custom_tag=include_custom_tag,
                exclude_custom_tag=exclude_custom_tag,
            )
        else:
            raise Exception(f"Issue with data form! {self.data_form}")

        logging.info(f"# Dataset-limit: {self.dataset_limit}")
        logging.info("#")
        logging.info("#")
        logging.info("# Dicom data information:")
        logging.info("#")
        logging.info(json.dumps(self.dicom_data_infos, indent=4, sort_keys=True))
        logging.info("#")
        logging.info("#")
        download_list = []
        for dicom_data_info in self.dicom_data_infos:
            if "dcm-uid" in dicom_data_info:
                dcm_uid = dicom_data_info["dcm-uid"]

                if "study-uid" not in dcm_uid:
                    raise Exception(
                        "study-uid not found in dcm-uid: {}".format(dcm_uid)
                    )
                if "series-uid" not in dcm_uid:
                    raise Exception(
                        "series-uid not found in dcm-uid: {}".format(dcm_uid)
                    )

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

            else:
                raise Exception(
                    "Error with dag-config!\nUnknown input: %s.\nSupported 'dcm-uid'.\nDag-conf: %s"
                    % (dicom_data_info, self.conf)
                )
        logging.info("")
        logging.info(f"## SERIES FOUND: {len(download_list)}")
        logging.info("")
        logging.info(f"## SERIES LIMIT: {self.dataset_limit}")
        download_list = (
            download_list[: self.dataset_limit]
            if self.dataset_limit is not None
            else download_list
        )
        logging.info("")
        logging.info(f"## SERIES TO LOAD: {len(download_list)}")
        logging.info("")
        if len(download_list) == 0:
            raise Exception("No series to download !!")
        series_download_fail = []
        self.dcmweb_helper = HelperDcmWeb(dag_run=kwargs["dag_run"])

        num_done = 0
        num_total = len(download_list)
        time_start = time.time()

        with ThreadPool(self.parallel_downloads) as threadpool:
            results = threadpool.imap_unordered(self.get_data, download_list)
            for download_successful, series_uid in results:
                if not download_successful:
                    series_download_fail.append(series_uid)

                num_done += 1

                if num_done % 10 == 0:
                    time_elapsed = time.time() - time_start
                    logging.info(f"{num_done}/{num_total} done")
                    # Format nicely in minutes and seconds
                    logging.info(
                        "Time elapsed: %d:%02d minutes" % divmod(time_elapsed, 60)
                    )
                    # Format nicely in minutes and seconds
                    logging.info(
                        "Estimated time remaining: %d:%02d minutes"
                        % divmod(time_elapsed / num_done * (num_total - num_done), 60)
                    )
                    # Log how many series are being downloaded per second on average
                    logging.info("Series per second: %.2f" % (num_done / time_elapsed))

            if len(series_download_fail) > 0:
                raise Exception(
                    "Some series could not be downloaded: {}".format(
                        series_download_fail
                    )
                )

        logging.info("## All series downloaded successfully")

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

        super().__init__(
            dag=dag,
            name=name,
            batch_name=batch_name,
            python_callable=self.start,
            max_active_tis_per_dag=10,
            execution_timeout=timedelta(minutes=60),
            **kwargs,
        )
