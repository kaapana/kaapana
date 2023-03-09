from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
import requests
import os
from os.path import join, exists, dirname, basename
import glob
from datetime import datetime


class LocalGetMetricsOperator(KaapanaPythonBaseOperator):
    def get_metrics(self):
        try:
            response = requests.get(
                self.metrics_endpoint, timeout=self.timeout, verify=self.verify_ssl
            )
        except requests.exceptions.Timeout:
            return None
        except requests.exceptions.TooManyRedirects:
            return None
        except requests.exceptions.RequestException as e:
            return None
        
        return response.text

    def write_metrics_to_file(self, metrics, metrics_output_dir):
        target_file_path = join(metrics_output_dir, f"{self.component_id}.txt")
        with open(target_file_path, "w") as the_file:
            the_file.write(metrics)

    def start(self, ds, **kwargs):
        print("Start LocalGetMetricsOperator ...")
        conf = kwargs["dag_run"].conf

        run_dir = join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        metrics_output_dir = join(run_dir, self.batch_name, self.operator_out_dir)
        os.makedirs(metrics_output_dir, exist_ok=True)
        component_metrics = LocalGetMetricsOperator.get_metrics()
        assert component_metrics != None
        LocalGetMetricsOperator.write_metrics_to_file(
            metrics=component_metrics, metrics_output_dir=metrics_output_dir
        )

    def __init__(
        self, dag, metrics_endpoint, component_id, timeout=5, verify_ssl=False, **kwargs
    ):
        self.metrics_endpoint = metrics_endpoint
        self.component_id = component_id
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        super().__init__(
            dag=dag,
            name="get-metrics",
            parallel_id=component_id,
            python_callable=self.start,
            **kwargs,
        )
