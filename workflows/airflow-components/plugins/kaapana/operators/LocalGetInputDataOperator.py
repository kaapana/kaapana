# -*- coding: utf-8 -*-

import os
import json
from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
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

        return download_successful, seriesUID

    def start(self, ds, **kwargs):
        print("Starting moule LocalGetInputDataOperator...")
        self.conf = kwargs['dag_run'].conf

        if self.cohort_limit is None and self.inputs is None and self.conf is not None and "conf" in self.conf:
            trigger_conf = self.conf["conf"]
            self.cohort_limit = int(trigger_conf["cohort_limit"] if "cohort_limit" in trigger_conf else None)

        dag_run_id = kwargs['dag_run'].run_id

        if self.inputs is None and self.conf == None or not "inputs" in self.conf:
            print("No config or inputs in config found!")
            print("Skipping...")
            return

        if self.inputs is None:
            self.inputs = self.conf["inputs"]

        if not isinstance(self.inputs, list):
            inputs = [self.inputs]

        download_list = []
        for input in self.inputs:
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

                    print("# Found elastic result:")
                    print("#")
                    print(f"# modality:  {modality}")
                    print(f"# studyUID:  {study_uid}")
                    print(f"# seriesUID: {series_uid}")
                    print("#")
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
            exit(1)

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
            exit(1)

    def __init__(self,
                 dag,
                 inputs=None,
                 name="get-input-data",
                 data_type="dicom",
                 check_modality=False,
                 cohort_limit=None,
                 parallel_downloads=3,
                 batch_name=None,
                 *args,
                 **kwargs):

        self.inputs = inputs
        self.data_type = data_type
        self.cohort_limit = cohort_limit
        self.check_modality = check_modality
        self.parallel_downloads = parallel_downloads

        super().__init__(
            dag,
            name=name,
            batch_name=batch_name,
            python_callable=self.start,
            task_concurrency=10,
            execution_timeout=timedelta(minutes=60),
            *args, **kwargs
        )
