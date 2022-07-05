# -*- coding: utf-8 -*-

import os
import json
from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.HelperElasticsearch import HelperElasticsearch
from multiprocessing.pool import ThreadPool
from os.path import join, exists, dirname
import shutil
import glob
import pydicom
from kaapana.operators.HelperCaching import cache_operator_output

class LocalGetInputDataOperator(KaapanaPythonBaseOperator):
    """
    Operator to get input data for a workflow/dag.

    This operator pulls all defined files from it's defined source and stores the files in the workflow directory.
    All subsequent operators can get and process the files from within the workflow directory.
    Typacally this operator can be used as the first operator in a workflow.

    **Inputs:**

    * inputs: 'dcm-uid' or 'elastic-query'
    * data_type: 'dicom' or 'json'
    * cohort_limit: limit the download series list number

    **Outputs:**

    * Stores downloaded 'dicoms' or 'json' files in the 'operator_out_dir'
    """

    def check_dag_modality(self, input_modality):
        # config = self.conf["conf"] if "conf" in self.conf else None
        config = self.conf
        input_modality = input_modality.lower()
        if config is not None and "form_data" in config and config["form_data"] is not None and "input" in config[
            "form_data"]:
            dag_modality = config["form_data"]["input"].lower()
            if dag_modality == "ct" or dag_modality == "mri" or dag_modality == "mrt" or dag_modality == "seg" or dag_modality == "ot":
                if input_modality != dag_modality:
                    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                    print("")
                    print("check_dag_modality failed!")
                    print("DAG modality vs input modality: {} vs {}".format(dag_modality, input_modality))
                    print("Wrong modality for this DAG!")
                    print("ABORT")
                    print("")
                    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                    raise ValueError('ERROR')

            else:
                print(f"DAG modality: {dag_modality} is not supported!")
                print("Supported modalities: CT,MRI,MRT,SEG,OT")
                print("Skipping 'check_dag_modality'")
                return

        else:
            print("Could not find DAG modality in DAG-run conf!")
            print("Skipping 'check_dag_modality'")
            return

    def get_data(self, series_dict):
        download_successful = True
        studyUID, seriesUID, dag_run_id = series_dict["studyUID"], series_dict["seriesUID"], series_dict["dag_run_id"]
        print(f"Start download series: {seriesUID}")
        target_dir = os.path.join(self.workflow_dir, dag_run_id, self.batch_name, f'{seriesUID}', self.operator_out_dir)
        print(f"# Target_dir: {target_dir}")

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        if self.data_type == "dicom":
            download_successful = HelperDcmWeb.downloadSeries(
                seriesUID=seriesUID,
                target_dir=target_dir
            )
            if not download_successful:
                print("Could not download DICOM data!")
                download_successful = False

        elif self.data_type == "json":
            meta_data = HelperElasticsearch.get_series_metadata(series_uid=seriesUID)
            json_path = join(target_dir, "metadata.json")
            with open(json_path, 'w') as fp:
                json.dump(meta_data, fp, indent=4, sort_keys=True)

        elif self.data_type == "minio":
            print("Not supported yet!")
            print("abort...")
            download_successful = False

        else:
            print("unknown data-mode!")
            print("abort...")
            download_successful = False

        return download_successful, seriesUID

    def move_series(self, dag_run_id: str, series_uid: str, dcm_path: str):
        print("#")
        print("############################ Get input data ############################")
        print("#")
        print(f"# SeriesUID:  {series_uid}")
        print(f"# RUN_id:     {dag_run_id}")
        print("#")
        target = join("/data", dag_run_id, "batch", series_uid, self.operator_out_dir)

        print("#")
        print(f"# Moving data from {dcm_path} -> {target}")
        print("#")
        shutil.move(src=dcm_path, dst=target)
        print(f"# Series CTP import -> OK: {series_uid}")

    @cache_operator_output
    def start(self, ds, **kwargs):
        print("# Starting moule LocalGetInputDataOperator...")
        print("#")
        self.conf = kwargs['dag_run'].conf

        # if self.cohort_limit is None and self.inputs is None and self.conf is not None and "conf" in self.conf:
        #     trigger_conf = self.conf["conf"]
        if self.cohort_limit is None and self.inputs is None and self.conf is not None:
            trigger_conf = self.conf
            self.cohort_limit = int(trigger_conf["cohort_limit"]) if "cohort_limit" in trigger_conf and trigger_conf["cohort_limit"] is not None else None
            if "elasticsearch_form" in trigger_conf:
                elasticsearch_data = trigger_conf["elasticsearch_form"]
                self.cohort_limit = int(elasticsearch_data["cohort_limit"]) if ("cohort_limit" in elasticsearch_data and elasticsearch_data["cohort_limit"] is not None) else None

        print(f"# Cohort-limit: {self.cohort_limit}")
        print("#")

        dag_run_id = kwargs['dag_run'].run_id
        if self.conf and ("seriesInstanceUID" in self.conf):
            series_uid = self.conf.get('seriesInstanceUID')
            dcm_path = join("/ctpinput", self.conf.get('dicom_path'))
            print("#")
            print(f"# Dicom-path: {dcm_path}")

            if not os.path.isdir(dcm_path):
                print(f"Could not find dicom dir: {dcm_path}")
                print("Abort!")
                raise ValueError('ERROR')
            self.move_series(dag_run_id, series_uid, dcm_path)
            return
        if self.conf and "ctpBatch" in self.conf:
            batch_folder = join("/ctpinput", self.conf.get('dicom_path'))
            print(f"# Batch folder: {batch_folder}")
            dcm_series_paths = [f for f in glob.glob(batch_folder+"/*")]
            for dcm_series_path in dcm_series_paths:
                dcm_file_list = glob.glob(dcm_series_path + "/*.dcm", recursive=True)
                if dcm_file_list:
                    dcm_file = pydicom.dcmread(dcm_file_list[0], force=True)
                    series_uid = dcm_file[0x0020, 0x000E].value
                    self.move_series(dag_run_id, series_uid, dcm_series_path)
            # remove parent batch folder
            if not os.listdir(batch_folder):
                shutil.rmtree(batch_folder)
            return

        if self.conf and "dataInputDirs" in self.conf:
            dataInputDirs = self.conf.get('dataInputDirs')
            if not isinstance(dataInputDirs, list):
                dataInputDirs = [dataInputDirs]
            for src in dataInputDirs:
                target = join(dirname(src), self.operator_out_dir)
                if src == target:
                    print("#")
                    print(f"# Data is already at out dir location -> {target}")
                    print("#")
                else:
                    print("#")
                    print(f"# Moving data from {src} -> {target}")
                    print("#")
                    shutil.move(src=src, dst=target)
                    print("# Dag input dir correctly ajusted.")
            return

        if self.inputs is None and self.conf == None or not "inputs" in self.conf:
            print("No config or inputs in config found!")
            print("Skipping...")
            return

        if self.inputs is None:
            self.inputs = self.conf["inputs"]

        if not isinstance(self.inputs, list):
            self.inputs = [self.inputs]

        print("#")
        print("#")
        print("# Inputs:")
        print("#")
        print(json.dumps(self.inputs, indent=4, sort_keys=True))
        print("#")
        print("#")
        download_list = []
        for input in self.inputs:
            if "elastic-query" in input:
                elastic_query = input["elastic-query"]
                if "query" not in elastic_query:
                    print("'query' not found in 'elastic-query': {}".format(input))
                    print("abort...")
                    raise ValueError('ERROR')
                if "index" not in elastic_query:
                    print("'index' not found in 'elastic-query': {}".format(input))
                    print("abort...")
                    raise ValueError('ERROR')

                query = elastic_query["query"]
                index = elastic_query["index"]

                cohort = HelperElasticsearch.get_query_cohort(elastic_index=index, elastic_query=query)

                for series in cohort:
                    series = series["_source"]

                    study_uid = series[HelperElasticsearch.study_uid_tag]
                    series_uid = series[HelperElasticsearch.series_uid_tag]
                    # SOPInstanceUID = series[ElasticDownloader.SOPInstanceUID_tag]
                    modality = series[HelperElasticsearch.modality_tag]

                    print(f"# Found elastic result: {modality}: {series_uid}")
                    if self.check_modality:
                        print("# checking modality...")
                        self.check_dag_modality(input_modality=modality)

                    download_list.append(
                        {
                            "studyUID": study_uid,
                            "seriesUID": series_uid,
                            "dag_run_id": dag_run_id
                        }
                    )

            elif "dcm-uid" in input:
                dcm_uid = input["dcm-uid"]

                if "study-uid" not in dcm_uid:
                    print("'study-uid' not found in 'dcm-uid': {}".format(input))
                    print("abort...")
                    raise ValueError('ERROR')
                if "series-uid" not in dcm_uid:
                    print("'series-uid' not found in 'dcm-uid': {}".format(input))
                    print("abort...")
                    raise ValueError('ERROR')

                if "modality" in dcm_uid and self.check_modality:
                    modality = dcm_uid["modality"]
                    self.check_dag_modality(input_modality=modality)

                study_uid = dcm_uid["study-uid"]
                series_uid = dcm_uid["series-uid"]

                download_list.append(
                    {
                        "studyUID": study_uid,
                        "seriesUID": series_uid,
                        "dag_run_id": dag_run_id
                    }
                )

            else:
                print("Error with dag-config!")
                print("Unknown input: {}".format(input))
                print("Supported 'dcm-uid' and 'elastic-query' ")
                print("Dag-conf: {}".format(self.conf))
                raise ValueError('ERROR')

        print("")
        print(f"## SERIES FOUND: {len(download_list)}")
        print("")
        print(f"## SERIES LIMIT: {self.cohort_limit}")
        download_list = download_list[:self.cohort_limit] if self.cohort_limit is not None else download_list
        print("")
        print(f"## SERIES TO LOAD: {len(download_list)}")
        print("")
        if len(download_list) == 0:
            print("#####################################################")
            print("#")
            print(f"# No series to download !! ")
            print("#")
            print("#####################################################")
            raise ValueError('ERROR')
        series_download_fail = []
        results = ThreadPool(self.parallel_downloads).imap_unordered(self.get_data, download_list)
        for download_successful, series_uid in results:
            print(f"# Series download ok: {series_uid}")
            if not download_successful:
                series_download_fail.append(series_uid)

        if len(series_download_fail) > 0:
            print("#####################################################")
            print("#")
            print(f"# Some series could not be downloaded! ")
            for series_uid in series_download_fail:
                print("#")
                print(f"# Series: {series_uid} failed !")
                print("#")
            print("#####################################################")
            raise ValueError('ERROR')

    def __init__(self,
                 dag,
                 inputs=None,
                 name="get-input-data",
                 data_type="dicom",
                 check_modality=False,
                 cohort_limit=None,
                 parallel_downloads=3,
                 batch_name=None,
                 **kwargs):
        """
        :param inputs: 'dcm-uid' or 'elastic-query'.
        :param data_type: 'dicom' or 'json'
        :param check_modality: 'True' or 'False'
        :param cohort_limit: limits the download list
        :param parallel_downloads: default 3, number of parallel downloads
        """


        self.inputs = inputs
        self.data_type = data_type
        self.cohort_limit = cohort_limit
        self.check_modality = check_modality
        self.parallel_downloads = parallel_downloads

        super().__init__(
            dag=dag,
            name=name,
            batch_name=batch_name,
            python_callable=self.start,
            max_active_tis_per_dag=10,
            execution_timeout=timedelta(minutes=60),
            **kwargs
        )