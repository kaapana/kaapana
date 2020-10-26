# -*- coding: utf-8 -*-

import os
import json
from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR, INITIAL_INPUT_DIR

from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.HelperElasticsearch import HelperElasticsearch


class LocalGetInputDataOperator(KaapanaPythonBaseOperator):

    def check_dag_modality(self, input_modality):
        config = self.conf["conf"] if "conf" in self.conf else None
        input_modality = input_modality.lower()
        if config is not None and "form_data" in config and config["form_data"] is not None and "input" in config["form_data"]:
            dag_modality = config["form_data"]["input"].lower()
            if dag_modality == "ct" or dag_modality == "mri" or dag_modality == "mrt" or dag_modality == "seg":
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
                print("DAG modality: {} is not supported!")
                print("Supported modalities: CT,MRI,MRT,SEG")
                print("Skipping 'check_dag_modality'")
                return

        else:
            print("Could not find DAG modality in DAG-run conf!")
            print("Skipping 'check_dag_modality'")
            return

    def get_data(self, studyUID, seriesUID, dag_run_id):
        target_dir = os.path.join(WORKFLOW_DIR, dag_run_id, BATCH_NAME, f'{seriesUID}', INITIAL_INPUT_DIR)

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        if self.data_type == "dicom":
            HelperDcmWeb.downloadSeries(studyUID=studyUID, seriesUID=seriesUID, target_dir=target_dir)

        elif self.data_type == "json":
            meta_data = HelperElasticsearch.get_series_metadata(series_uid=seriesUID)
            json_path = os.path.join(target_dir, "metadata.json")
            with open(json_path, 'w') as fp:
                json.dump(meta_data, fp, indent=4, sort_keys=True)

        elif self.data_type == "minio":
            print("Not supported yet!")
            print("abort...")
            exit(1)

        else:
            print("unknown data-mode!")
            print("abort...")
            exit(1)

    def start(self, ds, **kwargs):
        print("Starting moule LocalGetInputDataOperator...")
        self.conf = kwargs['dag_run'].conf
        dag_run_id = kwargs['dag_run'].run_id

        if self.conf == None or not "inputs" in self.conf:
            print("No config or inputs in config found!")
            print("Skipping...")
            return

        inputs = self.conf["inputs"]

        if not isinstance(inputs, list):
            inputs = [inputs]

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

                    self.get_data(studyUID=study_uid, seriesUID=series_uid, dag_run_id=dag_run_id)

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

                self.get_data(studyUID=study_uid, seriesUID=series_uid, dag_run_id=dag_run_id)

            else:
                print("Error with dag-config!")
                print("Unknown input: {}".format(input))
                print("Supported 'dcm-uid' and 'elastic-query' ")
                print("Dag-conf: {}".format(self.conf))
                exit(1)

    def __init__(self,
                 dag,
                 data_type="dicom",
                 check_modality=False,
                 *args,
                 **kwargs):
        self.data_type = data_type
        self.check_modality = check_modality

        super().__init__(
            dag,
            name="get-input-data",
            python_callable=self.start,
            task_concurrency=10,
            execution_timeout=timedelta(minutes=15),
            *args, **kwargs
        )
