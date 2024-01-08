from minio import Minio
import os
import glob
import uuid
import json
from zipfile import ZipFile
import datetime
from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.HelperFederated import federated_sharing_decorator


class LocalFedartedSetupFederatedTestOperator(KaapanaPythonBaseOperator):
    @federated_sharing_decorator
    @cache_operator_output
    def start(self, ds, **kwargs):
        conf = kwargs["dag_run"].conf
        print("conf", conf)
        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)

        from_previous_json_path = os.path.join(
            run_dir, self.operator_in_dir, "from_previous.json"
        )
        with open(from_previous_json_path, "r", encoding="utf-8") as jsonData:
            print("Yippie from previous seems to be available")
            print(json.load(jsonData))

        json_output_path = os.path.join(run_dir, self.operator_out_dir, "model.json")
        if not os.path.exists(os.path.dirname(json_output_path)):
            os.makedirs(os.path.dirname(json_output_path))
        if os.path.isfile(json_output_path):
            with open(json_output_path, "r", encoding="utf-8") as jsonData:
                model = json.load(jsonData)
        else:
            model = {"epochs": [0]}
        with open(json_output_path, "w", encoding="utf-8") as jsonData:
            model["epochs"].append(model["epochs"][-1] + 1)
            json.dump(model, jsonData, indent=4, sort_keys=True, ensure_ascii=True)

        if (
            "simulate_fail_round" in conf["workflow_form"]
            and conf["workflow_form"]["simulate_fail_round"]
            == conf["federated_form"]["federated_round"]
        ):
            raise ValueError("Simulating an Error!")
        return

    def __init__(self, dag, **kwargs):
        super(LocalFedartedSetupFederatedTestOperator, self).__init__(
            dag=dag,
            name=f"federated-setup-federated-test",
            python_callable=self.start,
            allow_federated_learning=True,
            execution_timeout=timedelta(minutes=30),
            **kwargs,
        )
