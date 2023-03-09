from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
import requests
import glob
from os.path import join, basename, dirname, exists

INSTANCE_NAME = "Test 1"


class LocalPushToPromOperator(KaapanaPythonBaseOperator):
    def push_to_gateway(self, job_name, instance_name, data):
        headers = {"X-Requested-With": "Python requests", "Content-type": "text/xml"}
        url = f"{self.pushgateway_url}/metrics/job/{job_name}/instance/{instance_name}"
        assert job_name != ""
        # data = "websites_offline{website=\"example.com\"} 0\n"
        try:
            r = requests.post(
                url,
                headers=headers,
                data=data,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        except requests.exceptions.Timeout:
            pass
        except requests.exceptions.TooManyRedirects:
            pass
        except requests.exceptions.RequestException as e:
            pass
        print(r.reason)
        print(r.status_code)

    def start(self, ds, **kwargs):
        print("Start LocalPushToPromOperator ...")
        conf = kwargs["dag_run"].conf

        run_dir = join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = [f for f in glob(join(run_dir, self.batch_name, "*"))]

        for batch_element_dir in batch_folder:
            metrics_txt_files = sorted(
                glob(
                    join(batch_element_dir, self.operator_in_dir, "*.txt*"),
                    recursive=False,
                )
            )
            job_name = ""
            for metrics_file in metrics_txt_files:
                print(f"Prepare metrics from: {metrics_file}")

                job_name = ""
                metrics_data = ""
                with open(metrics_file) as file:
                    for line in file:
                        line_text = line.rstrip()
                        if "job_name:" in line_text:
                            job_name = line_text.split("job_name:")[-1]
                            metrics_data = ""
                        metrics_data += f"{line_text}\n"

                LocalPushToPromOperator.push_to_gateway(
                    self, job_name, instance_name=INSTANCE_NAME, data=metrics_data
                )

    def __init__(
        self,
        dag,
        pushgateway_url="pushgateway-service.extensions.svc:9091",
        timeout=5,
        verify_ssl=False,
        **kwargs,
    ):
        self.pushgateway_url = pushgateway_url
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        super().__init__(
            dag=dag,
            name="push-metrics-to-prometheus",
            python_callable=self.start,
            **kwargs,
        )
