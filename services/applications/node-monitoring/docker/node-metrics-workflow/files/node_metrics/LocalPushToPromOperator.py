from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
import requests
from glob import glob
from os.path import join, basename, dirname, exists
import json

class LocalPushToPromOperator(KaapanaPythonBaseOperator):
    def push_to_gateway(self, job_name, instance_name, data):
        headers = {"X-Requested-With": "Python requests", "Content-type": "text/xml"}
        url = f"{self.pushgateway_url}/metrics/job/{job_name}/instance/{instance_name}"
        assert job_name != None
        job_name = job_name.strip().replace(" ", "-")
        assert instance_name != None
        instance_name = instance_name.strip().replace(" ", "-")
        # data = "websites_offline{website=\"example.com\"} 0\n"
        print(f"Pushing {job_name=} {instance_name=}!")
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

        print("Request was ok!")
        print(response.text)

    def start(self, ds, **kwargs):
        global INSTANCE_NAME
        print("Start LocalPushToPromOperator ...")
        conf = kwargs["dag_run"].conf
        run_dir = join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = [f for f in glob(join(run_dir, self.batch_name, "*"))]

        prom_updates = {}
        for batch_element_dir in batch_folder:
            element_input_dir = join(batch_element_dir, self.operator_in_dir, "*.txt")
            print(f"# Searching for metrics.txt files in {element_input_dir}")
            aggregated_metrics_files = sorted(glob(element_input_dir, recursive=False))
            print(f"# Found {len(aggregated_metrics_files)} txt files.")

            for aggregated_metrics_file in aggregated_metrics_files:
                print(f"Prepare metrics from: {aggregated_metrics_file}")

                job_name = None
                instance_name = None
                timestamp = None
                metrics_data = ""
                with open(aggregated_metrics_file) as file:
                    for line in file:
                        line_text = line.rstrip()
                        if "instance_name:" in line_text:
                            instance_name = line_text.split("instance_name:")[-1].strip()
                            print(f"{instance_name=}")
                            if instance_name not in prom_updates: 
                                prom_updates[instance_name] = {}
                        elif "version:" in line_text:
                            version = line_text.split("version:")[-1].strip()
                            print(f"{version=}")
                        elif "timestamp:" in line_text:
                            timestamp = line_text.split("timestamp:")[-1].strip()
                            print(f"{timestamp=}")
                            assert instance_name != None
                            if timestamp not in prom_updates[instance_name]: 
                                prom_updates[instance_name][timestamp] = {}
                        elif "job_name:" in line_text:
                            job_name = line_text.split("job_name:")[-1].strip()
                            print(f"{job_name=}")
                            if metrics_data != "" and job_name not in prom_updates[instance_name][timestamp]:
                                prom_updates[instance_name][timestamp][job_name] = metrics_data
                            metrics_data = ""
                        else:
                            metrics_data += f"{line_text}\n"

        print(json.dumps(prom_updates,indent=4))
        for instance_name, timestamp_data in prom_updates.items():
            count_data_items = len(timestamp_data.keys())
            assert count_data_items != 0
            if count_data_items > 1:
                print(f"# Found multiple timestamps {timestamp_data.keys()}")
                latest_timestamp = sorted(timestamp_data.keys())[-1]
                print(f"# selected {latest_timestamp=}")
                timestamp_data = timestamp_data[latest_timestamp]
            else:
                timestamp_data = next(iter(timestamp_data))

            for job_name, metrics_data in timestamp_data.items():
                self.push_to_gateway(
                    job_name=job_name,
                    instance_name=instance_name,
                    data=metrics_data,
            )

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
