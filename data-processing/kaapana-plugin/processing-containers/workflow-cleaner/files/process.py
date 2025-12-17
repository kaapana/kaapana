#!/usr/bin/env python3
import json
import os
import shutil
from pathlib import Path


def main():
    """Cleanup workflow execution in workflow namespace."""

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

    print("[STEP 2] Cleaning workflow run directory...")
    if clean_workflow_dir:
        if workflow_dir.exists():
            try:
                print(f"[INFO] Cleaning directory: {workflow_dir}")
                shutil.rmtree(workflow_dir)
                print(f"[SUCCESS] Cleaned: {workflow_dir}")
            except Exception:
                print(f"[ERROR] Failed to clean {workflow_dir}")
                raise
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
