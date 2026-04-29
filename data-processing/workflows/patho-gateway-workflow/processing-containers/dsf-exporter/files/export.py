#!/usr/bin/env python3
import json
import os
import shutil
import sys
from pathlib import Path

INPUT_DIR = Path("/kaapana/input/dicom-psn")
OUTPUT_DIR = Path("/kaapana/output/export-report")
DEFAULT_EXPORT_TARGET = "/kaapana/mounted/export"


def log(message):
    print(message, flush=True)


def fail(message):
    raise RuntimeError(message)


def load_workflow_conf():
    try:
        from kaapanapy.helper import load_workflow_config

        return load_workflow_config()
    except Exception as exc:
        log(f"Could not load Kaapana workflow config via helper: {exc}")
    value = os.getenv("WORKFLOW_CONFIG_JSON") or os.getenv("DAGRUN_CONF_JSON")
    return json.loads(value) if value else {}


def get_conf_value(conf, key, default=None):
    if key in conf:
        return conf[key]
    workflow_form = conf.get("workflow_form") or {}
    if key in workflow_form:
        return workflow_form[key]
    upper_key = key.upper()
    if upper_key in workflow_form:
        return workflow_form[upper_key]
    return os.getenv(upper_key, default)


def main():
    conf = load_workflow_conf()
    export_target = Path(get_conf_value(conf, "export_target", DEFAULT_EXPORT_TARGET))

    log(f"Input directory: {INPUT_DIR}")
    log(f"Output directory: {OUTPUT_DIR}")
    log(f"Export target: {export_target}")
    if not INPUT_DIR.is_dir():
        fail(f"Input directory does not exist: {INPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    export_target.mkdir(parents=True, exist_ok=True)

    files = sorted(path for path in INPUT_DIR.rglob("*") if path.is_file() and path.suffix.lower() != ".json")
    log(f"Number of files found: {len(files)}")
    if not files:
        fail(f"No pseudonymized DICOM input files found in {INPUT_DIR}.")

    report = {"items": []}
    for path in files:
        target = export_target / path.name
        try:
            shutil.copy2(path, target)
        except Exception as exc:
            fail(f"Export failed for {path} -> {target}: {exc}")
        if not target.exists() or target.stat().st_size != path.stat().st_size:
            fail(f"Export failed for {path}; target file is missing or incomplete: {target}")
        report["items"].append({"file": path.name, "target": str(target), "status": "success"})
        log(f"{path.name}: exported to {target}")

    # TODO: Add DICOMweb export.
    # TODO: Add DSF API integration.
    report_path = OUTPUT_DIR / "export_report.json"
    with report_path.open("w") as f:
        json.dump(report, f, indent=2)
    log(f"Number of files written: {len(report['items'])}")
    log(f"Final report path: {report_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
