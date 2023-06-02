import os
import glob
import json
import datetime

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalConcatJsonOperator(KaapanaPythonBaseOperator):
    """
    Concatenate data from multiple json files in the dag_run directory into a single json file.

    **Inputs:**

        * Multiple json files

    **Outputs**

        * A single json file in the outpot directory of the operator

    """

    def start(self, ds, **kwargs):
        print("Starting module LocalConcatJsonOperator...")
        print(kwargs)

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_dirs = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))]
        timestamp = datetime.datetime.utcnow()
        json_output_path = os.path.join(
            run_dir, self.operator_out_dir, "{}-{}.json".format(timestamp, self.name)
        )
        if not os.path.exists(os.path.dirname(json_output_path)):
            os.makedirs(os.path.dirname(json_output_path))

        json_files = []
        for batch_element_dir in batch_dirs:
            batch_el_json_files = sorted(
                glob.glob(
                    os.path.join(
                        batch_element_dir, self.operator_in_dir, "**", "*.json*"
                    ),
                    recursive=True,
                )
            )
            for json_file in batch_el_json_files:
                with open(json_file) as data_file:
                    json_dict = json.load(data_file)
                json_files.append(json_dict)

        with open(json_output_path, "w", encoding="utf-8") as jsonData:
            json.dump(json_files, jsonData, indent=4, sort_keys=True)

    def __init__(self, dag, name="concatenated", **kwargs):
        """
        :param name: Used in the filename of the output json file i.e. :code:`timestamp-name.json`. Defaults to "concatenated".
        :type name: str
        """
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
