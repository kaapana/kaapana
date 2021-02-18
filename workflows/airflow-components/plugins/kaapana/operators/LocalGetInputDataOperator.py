# -*- coding: utf-8 -*-

import os
import json
from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.HelperElasticsearch import HelperElasticsearch
from multiprocessing.pool import ThreadPool


class LocalGetInputDataOperator(KaapanaPythonBaseOperator):

    def check_dag_modality(self, input_modality):
        config = self.conf["conf"] if "conf" in self.conf else None
        input_modality = input_modality.lower()
        if config is not None and "form_data" in config and config["form_data"] is not None and "input" in config["form_data"]:
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
                    exit(1)

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
        target_dir = os.path.join(WORKFLOW_DIR, dag_run_id, BATCH_NAME, f'{seriesUID}', self.operator_out_dir)

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
            json_path = os.path.join(target_dir, "metadata.json")
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

        message = f"Series: {seriesUID}"
        return download_successful, message

    def start(self, ds, **kwargs):
        print("Starting moule LocalGetInputDataOperator...")
        self.conf = kwargs['dag_run'].conf

        cohort_limit = None
        if self.conf is not None and "conf" in self.conf:
            trigger_conf = self.conf["conf"]
            cohort_limit = int(trigger_conf["cohort_limit"] if "cohort_limit" in trigger_conf else None)

        dag_run_id = kwargs['dag_run'].run_id

        if self.conf == None or not "inputs" in self.conf:
            print("No config or inputs in config found!")
            print("Skipping...")
            return

        inputs = self.conf["inputs"]

        if not isinstance(inputs, list):
            inputs = [inputs]

        download_list = []
        for input in inputs:
            if "elastic-query" in input:
                elastic_query = input["elastic-query"]
                if "query" not in elastic_query:
                    print("'query' not found in 'elastic-query': {}".format(input))
                    print("abort...")
                    exit(1)
                if "index" not in elastic_query:
                    print("'index' not found in 'elastic-query': {}".format(input))
                    print("abort...")
                    exit(1)

                query = elastic_query["query"]
                index = elastic_query["index"]

                cohort = HelperElasticsearch.get_query_cohort(elastic_index=index, elastic_query=query)

                for series in cohort:
                    series = series["_source"]

                    study_uid = series[HelperElasticsearch.study_uid_tag]
                    series_uid = series[HelperElasticsearch.series_uid_tag]
                    # SOPInstanceUID = series[ElasticDownloader.SOPInstanceUID_tag]
                    modality = series[HelperElasticsearch.modality_tag]
                    print(("studyUID %s" % study_uid))
                    print(("seriesUID %s" % series_uid))
                    print(("modality %s" % modality))
                    if self.check_modality:
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
                    exit(1)
                if "series-uid" not in dcm_uid:
                    print("'series-uid' not found in 'dcm-uid': {}".format(input))
                    print("abort...")
                    exit(1)

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
                exit(1)

        download_list = download_list[:cohort_limit] if cohort_limit is not None else download_list
        print("")
        print("## SERIES TO LOAD: {}".format(len(download_list)))
        print("")

        results = ThreadPool(self.parallel_downloads).imap_unordered(self.get_data, download_list)
        for download_successful, message in results:
            print(f"Finished: {message}")
            if not download_successful:
                print("Something went wrong.")
                exit(1)

    def __init__(self,
                 dag,
                 data_type="dicom",
                 check_modality=False,
                 parallel_downloads=3,
                 *args,
                 **kwargs):
        self.data_type = data_type
        self.check_modality = check_modality
        self.parallel_downloads = parallel_downloads

        super().__init__(
            dag,
            name="get-input-data",
            python_callable=self.start,
            task_concurrency=10,
            execution_timeout=timedelta(minutes=60),
            *args, **kwargs
        )
