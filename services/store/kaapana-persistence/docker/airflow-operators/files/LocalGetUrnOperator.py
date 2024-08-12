# -*- coding: utf-8 -*-

import os
from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from persistence.HelperPersistence import URNClient
from multiprocessing.pool import ThreadPool
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE


class LocalGetUrnOperator(KaapanaPythonBaseOperator):
    @cache_operator_output
    def start(self, ds, **kwargs):
        self.conf = kwargs["dag_run"].conf

        dag_run_id = kwargs["dag_run"].run_id

        urns = []
        if self.conf and "urns" in self.conf:
            conf_urns = self.conf.get("urns")
            if not isinstance(urns, list):
                conf_urns = [conf_urns]
            urns.extend(conf_urns)
        else:
            print(self.conf)
            print("#")
            print(f"# No URNs in conf object")
            print("#")

        if "form_data" in self.conf:
            urns.extend(
                [x.strip() for x in self.conf["form_data"].get("urns", "").split(",")]
            )

        if not urns:
            print("# No URNs to download")
            exit(1)

        # if self.conf is not None and "data_form" in self.conf:
        #     self.data_form = self.conf["data_form"]

        # if self.data_form is None:
        #     print(
        #         "No data_form in config or object found! Data seems to be present already..."
        #     )
        #     print("Skipping...")
        #     return

        # print("# data_form:")
        # print("#")
        # print(json.dumps(self.data_form, indent=4, sort_keys=True))
        # print("#")
        # print("#")

        # dataset_limit = int(self.data_form.get("dataset_limit", 0))
        # self.dataset_limit = dataset_limit if dataset_limit > 0 else None

        # if len(self.data_form["identifiers"]) > 0:
        #     self.dicom_data_infos = HelperOpensearch.get_dcm_uid_objects(
        #         self.data_form["identifiers"]
        #     )
        # else:
        #     print("# Issue with data form -> exit. ")
        #     exit(1)

        # print(f"# Dataset-limit: {self.dataset_limit}")
        # print("#")
        # print("#")

        def download(urn):
            print(f"Start download object: {urn}")
            target = os.path.join(
                self.airflow_workflow_dir,
                dag_run_id,
                self.batch_name,
                # f"{seriesUID}",
                self.operator_out_dir,
                urn,
            )

            print(f"# Target: {target}")

            target_dir = os.path.dirname(target)
            os.makedirs(target_dir, exist_ok=True)

            try:
                self.urn_client.download(urn, target)
                return True, urn
            except Exception as e:
                return False, urn

        download_failed = []
        with ThreadPool(self.parallel_downloads) as threadpool:
            results = threadpool.imap_unordered(download, urns)
            for download_successful, urn in results:
                print(f"# URN download ok: {urn}")
                if not download_successful:
                    download_failed.append(urn)

            if len(download_failed) > 0:
                print("#####################################################")
                print("#")
                print(f"# Some objects could not be downloaded! ")
                for urn in download_failed:
                    print("#")
                    print(f"# Object: {urn} failed !")
                    print("#")
                print("#####################################################")
                raise ValueError("ERROR")

    def __init__(
        self,
        dag,
        name="get-urn-data",
        data_form=None,
        dataset_limit=None,
        parallel_downloads=3,
        batch_name=None,
        urn_base_api: str = f"http://kaapana-persistence-service.{SERVICES_NAMESPACE}.svc:8080/urn",
        **kwargs,
    ):
        """
        :param data_form: 'json'
        :param dataset_limit: limits the download list
        :param parallel_downloads: default 3, number of parallel downloads
        """

        self.data_form = data_form
        self.dataset_limit = dataset_limit
        self.parallel_downloads = parallel_downloads
        self.urn_client = URNClient(urn_base_api)

        super().__init__(
            dag=dag,
            name=name,
            batch_name=batch_name,
            python_callable=self.start,
            max_active_tis_per_dag=10,
            execution_timeout=timedelta(minutes=60),
            **kwargs,
        )
