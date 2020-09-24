# -*- coding: utf-8 -*-

import os
import json
from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR, INITIAL_INPUT_DIR

from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.HelperElasticsearch import HelperElasticsearch

class LocalGetInputDataOperator(KaapanaPythonBaseOperator):

    def get_data(self, studyUID, seriesUID, dag_run_id):
        target_dir = os.path.join(WORKFLOW_DIR, dag_run_id, BATCH_NAME, f'{seriesUID}', INITIAL_INPUT_DIR)

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        if self.data_type == "dicom":
            HelperDcmWeb.downloadSeries(studyUID=studyUID, seriesUID=seriesUID, dag_run_id=dag_run_id, target_dir=target_dir)

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
        conf = kwargs['dag_run'].conf
        dag_run_id = kwargs['dag_run'].run_id
        print(conf)

        if conf == None:
            print("No config found!")
            print("Skipping...")
            return

        if not "inputs" in conf:
            print("Error with dag-config!")
            print("Could not identify 'inputs'")
            print("Dag-conf: {}".format(conf))
            exit(1)

        inputs = conf["inputs"]

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

                study_uid = dcm_uid["study-uid"]
                series_uid = dcm_uid["series-uid"]

                self.get_data(studyUID=study_uid, seriesUID=series_uid, dag_run_id=dag_run_id)

            else:
                print("Error with dag-config!")
                print("Unknown input: {}".format(input))
                print("Supported 'dcm-uid' and 'elastic-query' ")
                print("Dag-conf: {}".format(conf))
                exit(1)

    def __init__(self,
                 dag,
                 data_type="dicom",
                 *args,
                 **kwargs):
        self.data_type = data_type

        super().__init__(
            dag,
            name="get-input-data",
            python_callable=self.start,
            task_concurrency=10,
            execution_timeout=timedelta(minutes=15),
            *args, **kwargs
        )
