#!/usr/bin/env python3
import json
import os
import shutil
from pathlib import Path
from kaapanapy.helper import load_workflow_config

def clean_previous_dag_run(airflow_workflow_dir, conf, run_identifier):
    if (
        conf is not None
        and "federated_form" in conf
        and conf["federated_form"] is not None
    ):
        federated = conf["federated_form"]
        if run_identifier in federated and federated[run_identifier] is not None:
            dag_run_dir = os.path.join(
                airflow_workflow_dir, conf["federated_form"][run_identifier]
            )
            print(f"Removing batch files from {run_identifier}: {dag_run_dir}")
            if os.path.isdir(dag_run_dir):
                shutil.rmtree(dag_run_dir)

def main():
    """Main cleanup workflow execution."""
    
    print("##################################################")
    print("#")
    print("# Starting Workflow-Cleanup ...")
    print("#")
    print("##################################################")
    print()
    
    workflow_dir = os.getenv("WORKFLOW_DIR", "")
    if not workflow_dir:
        print("[ERROR] WORKFLOW_DIR environment variable not set")
        return 1

    print(f"[INFO] Workflow directory: {workflow_dir}")

    clean_workflow_dir = os.getenv("CLEAN_WORKFLOW_DIR", "true").lower() == "true"
    print(f"[INFO] Clean workflow directory: {clean_workflow_dir}")

    workflow_dir = Path(workflow_dir)

    # ===== Load Configuration =====
    if clean_workflow_dir:
        conf_path = workflow_dir.parent / "conf" / f"{workflow_dir.name}.json"
        if not conf_path.exists():
            print(f"[ERROR] Config file not found: {conf_path}")
            return 1
        with open(conf_path, "r") as f:
            conf = json.load(f)
    else:
        conf = load_workflow_config()

    print(f"[INFO] Loaded config (keys): {list(conf.keys())}")

    print("[STEP 1] Cleaning previous DAG run artifacts...")
    airflow_workflow_dir = workflow_dir.parent
    clean_previous_dag_run(airflow_workflow_dir, conf, "from_previous_dag_run")
    clean_previous_dag_run(airflow_workflow_dir, conf, "before_previous_dag_run")

    print("[STEP 2] Cleaning workflow run directory...")
    if clean_workflow_dir:
        if workflow_dir.exists():
            try:
                print(f"[INFO] Cleaning directory: {workflow_dir}")
                shutil.rmtree(workflow_dir)
                print(f"[SUCCESS] Cleaned: {workflow_dir}")
            except Exception as e:
                print(f"[ERROR] Failed to clean {workflow_dir}: {e}")
                return 1
        else:
            print(f"[INFO] Directory does not exist (skip): {workflow_dir}")
    else:
        print("[INFO] Workflow directory cleaning disabled")
    
    print("##################################################")
    print("#")
    print("# Workflow-Cleanup completed successfully!")
    print("#")
    print("##################################################")
    return 0


if __name__ == "__main__":
    exit(main())