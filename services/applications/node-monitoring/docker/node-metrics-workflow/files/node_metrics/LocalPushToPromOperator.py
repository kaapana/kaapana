from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
import requests
from glob import glob
from os.path import join, basename, dirname, exists

INSTANCE_NAME = "Test-1"

class LocalPushToPromOperator(KaapanaPythonBaseOperator):
    def push_to_gateway(self, job_name, instance_name, data):
        headers = {"X-Requested-With": "Python requests", "Content-type": "text/xml"}
        url = f"{self.pushgateway_url}/metrics/job/{job_name}/instance/{instance_name}"
        assert job_name != ""
        # data = "websites_offline{website=\"example.com\"} 0\n"
        try:
            response = requests.post(
                url,
                headers=headers,
                data=data,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        except requests.exceptions.Timeout:
            print("Post request error! - Timeout")
        except requests.exceptions.TooManyRedirects:
            print("Post request error! - TooManyRedirects")
            exit(1)
        except requests.exceptions.RequestException as e:
            print("Post request error! - RequestException")
            print(str(e))
            exit(1)

        if response.status_code != 200:
            print(f"# ERROR! Status code: {response.status_code}!")
            print(f"# Text: {response.text}!")
            exit(1)

        print(response.reason)

    def start(self, ds, **kwargs):
        global INSTANCE_NAME
        print("Start LocalPushToPromOperator ...")
        conf = kwargs["dag_run"].conf

        run_dir = join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        txt_input_dir = join(run_dir, self.batch_name, self.operator_in_dir)
        assert exists(txt_input_dir)

        metrics_txt_files = glob(join(txt_input_dir,"*.txt*"),recursive=False)
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
                    else:
                        metrics_data += f"{line_text}\n"

            job_name = job_name.strip().replace(" ","-")
            INSTANCE_NAME = INSTANCE_NAME.strip().replace(" ","-")
            self.push_to_gateway(job_name=job_name, instance_name=INSTANCE_NAME, data=metrics_data)

    def __init__(
        self,
        dag,
        pushgateway_url="http://pushgateway-service.extensions.svc:9091",
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
