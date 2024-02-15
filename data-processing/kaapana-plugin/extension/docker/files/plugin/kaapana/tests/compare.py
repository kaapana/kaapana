from argparse import Namespace
import os
from generator import generate_test_dicoms
from helpers import compare_jsons
from pathlib import Path
from LocalDcm2JsonRefactoredOperator import LocalDcm2JsonRefOperator
from LocalDcm2JsonOperator import LocalDcm2JsonOperator
import time

os.environ["DCMDICTPATH"] = "/home/m395c/kaapana/services/flow/airflow/docker/files/scripts/dicom.dic"
os.environ["DICT_PATH"] = "/home/m395c/kaapana/services/flow/airflow/docker/files/scripts/dicom_tag_dict.json"


def main():
    workflow_dir = Path(
        "/home/m395c/kaapana/data-processing/kaapana-plugin/extension/docker/files/plugin/kaapana"
    )

    workflow_dir.mkdir(exist_ok=True, parents=True)

    dag_run = Namespace(run_id="tests")
    batch_name = "data"
    operator_in_dir = ""

    generate_dir = workflow_dir / dag_run.run_id / batch_name / "gens"
    generate_test_dicoms(generate_dir)

    print(f"###################################")
    print(f"########## VERSION: OLD ###########")
    print(f"###################################")
    start = time.time()
    opi = LocalDcm2JsonOperator(
        dag=None, workflow_dir=workflow_dir, batch_name=batch_name, operator_in_dir=operator_in_dir, operator_out_dir="old_json", bulk=True)
    opi.start(ds=None, dag_run=dag_run)
    end = time.time()
    total_time_old = end - start

    print(f"###################################")
    print(f"########## VERSION: NEW ###########")
    print(f"###################################")
    start = time.time()
    opi = LocalDcm2JsonRefOperator(
        dag=None, workflow_dir=workflow_dir, batch_name=batch_name, operator_in_dir=operator_in_dir, operator_out_dir="new_json", bulk=True)
    opi.start(ds=None, dag_run=dag_run)
    end = time.time()
    total_time_new = end - start

    print("####################################################################")
    print("############## !!!!!! DIFF !!!!!!!!#################################")
    print("####################################################################")
    print(f"Total time old: {total_time_old}")
    print(f"Total time new: {total_time_new}")
    compare_jsons(workflow_dir / dag_run.run_id / "old_json",
                  workflow_dir / dag_run.run_id / "new_json")
    print("####################################################################")
    print("####################################################################")
    print("####################################################################")


if __name__ == "__main__":
    main()
