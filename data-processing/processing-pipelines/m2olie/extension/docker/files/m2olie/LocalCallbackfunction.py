import os
import shutil
import time
import requests
from pathlib import Path
from typing import List, Dict
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_utils import get_release_name
from kaapana.blueprints.kaapana_global_variables import (
    PROCESSING_WORKFLOW_DIR,
    ADMIN_NAMESPACE,
    SERVICES_NAMESPACE,
    JOBS_NAMESPACE,
)


class LocalCallbackfunction(KaapanaPythonBaseOperator):
    """
    Reads Conf for needed parameters and calls the them.
    """

    HELM_API = f"http://kube-helm-service.{ADMIN_NAMESPACE}.svc:5000"
    TIMEOUT = 60 * 12

    def start(self, ds, **kwargs):
        print(kwargs["run_id"])
        print(kwargs["dag_run"].conf)
        workflow_from = kwargs["dag_run"].conf["data_form"]["workflow_form"]
        print(workflow_from)
        release_name = get_release_name(kwargs)
        t_end = time.time() + LocalCallbackfunction.TIMEOUT
        while time.time() < t_end:
            time.sleep(15)
            url = f"{LocalCallbackfunction.HELM_API}/view-chart-status"
            r = requests.get(url, params={"release_name": release_name})
            if r.status_code == 200:
                print("send-request to prometheus.")
                print(r.content)
                url = f"{LocalCallbackfunction.HELM_API}/pending-applications"
                r = requests.get(url)
                if r.status_code == 200:
                    applications = r.json()
                    release = next(
                        (
                            item
                            for item in applications
                            if item["releaseName"] == release_name
                        ),
                        None,
                    )
                    if release:
                        print(release)
                        print("Sending result to Prometheus!")
                        url = workflow_from["prometheus_uri"] + "/setState"
                        print("URL: ", url)
                        payload = {
                            "Kaapana.Dag.Link": {
                                "Type": "System.String",
                                "Value": release["links"][0],
                                "Uri": "",
                            }
                        }
                        print("payload: ", payload)
                        params = {
                            "processInstanceLabel": workflow_from[
                                "process_instance_label"
                            ],
                            "taskLabel": workflow_from["task_label"],
                            "newTaskState": "Completed",
                        }
                        print("params: ", params)
                        response = requests.post(url, params=params, json=payload)
                        print(response.status_code)
                        if (
                            not response.status_code == 200
                            or response.status_code == 201
                        ):
                            print(
                                "Something whent wrong, could not send the link to prometheus."
                            )
                            print("Response: ", response.content)
                            exit(1)
                        else:
                            print("Response: ", response.content)
                        return
                    else:
                        print("No matching result found.")
            if r.status_code == 500 or r.status_code == 404:
                print(f"Release {release_name} was uninstalled. My job is done here!")
                break
            r.raise_for_status()

    def __init__(self, dag, name="callback-function", **kwargs):
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
