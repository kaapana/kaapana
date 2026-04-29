#!/usr/bin/env python3
import csv
import json
import os
import sys
from pathlib import Path

INPUT_DIR = Path("/kaapana/input/dicom-label-removed")
OUTPUT_DIR = Path("/kaapana/output/dicom-psn")
DEFAULT_MAPPING_FILE = "/kaapana/mounted/mapping/mapping.csv"


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


def load_manifest():
    manifest_path = INPUT_DIR / "manifest.json"
    if not manifest_path.is_file():
        return {}
    with manifest_path.open() as f:
        manifest = json.load(f)
    mapping = {}
    for item in manifest.get("items", []):
        local_filename = item.get("local_filename")
        slide_id = item.get("slide_id")
        if local_filename and slide_id:
            mapping[Path(local_filename).stem] = slide_id
    return mapping


def load_mapping(mapping_file):
    if not mapping_file.is_file():
        fail(f"Pseudonym mapping file is missing: {mapping_file}")
    mapping = {}
    with mapping_file.open(newline="") as f:
        reader = csv.DictReader(f)
        if "slide_id" not in reader.fieldnames or "pseudonym" not in reader.fieldnames:
            fail("Pseudonym mapping CSV must contain 'slide_id' and 'pseudonym' columns.")
        for row in reader:
            slide_id = (row.get("slide_id") or "").strip()
            pseudonym = (row.get("pseudonym") or "").strip()
            if slide_id and pseudonym:
                mapping[slide_id] = pseudonym
    return mapping


def resolve_slide_id(path, manifest_map):
    stem = path.stem
    if stem in manifest_map:
        return manifest_map[stem]
    base_stem = stem.rsplit("_", 1)[0] if "_" in stem else stem
    if base_stem in manifest_map:
        return manifest_map[base_stem]
    return base_stem


def pseudonymize_dataset(dataset, pseudonym, remove_private_tags):
    dataset.PatientID = pseudonym
    dataset.PatientName = pseudonym
    dataset.AccessionNumber = pseudonym
    if "StudyID" in dataset:
        dataset.StudyID = pseudonym
    if remove_private_tags:
        dataset.remove_private_tags()
    # TODO: Final metadata policy for SlideID, nPSN, accession number, and private tags.
    return dataset


def main():
    import pydicom

    conf = load_workflow_conf()
    mapping_file = Path(get_conf_value(conf, "pseudonym_mapping_file", DEFAULT_MAPPING_FILE))
    remove_private_tags = str(get_conf_value(conf, "remove_private_tags", "true")).lower() == "true"

    log(f"Input directory: {INPUT_DIR}")
    log(f"Output directory: {OUTPUT_DIR}")
    log(f"Pseudonym mapping file: {mapping_file}")
    if not INPUT_DIR.is_dir():
        fail(f"Input directory does not exist: {INPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_map = load_manifest()
    pseudonym_map = load_mapping(mapping_file)
    files = sorted(path for path in INPUT_DIR.rglob("*") if path.is_file() and path.suffix.lower() != ".json")
    log(f"Number of files found: {len(files)}")
    if not files:
        fail(f"No DICOM input files found in {INPUT_DIR}.")

    report = {"items": []}
    for path in files:
        slide_id = resolve_slide_id(path, manifest_map)
        if slide_id not in pseudonym_map:
            fail(f"SlideID '{slide_id}' is not found in pseudonym mapping file {mapping_file}.")
        pseudonym = pseudonym_map[slide_id]
        target = OUTPUT_DIR / f"{pseudonym}.dcm"
        if target.exists():
            target = OUTPUT_DIR / f"{pseudonym}_{len(report['items']) + 1:04d}.dcm"

        try:
            dataset = pydicom.dcmread(path)
        except Exception as exc:
            fail(f"DICOM reading failed for {path}: {exc}")
        dataset = pseudonymize_dataset(dataset, pseudonym, remove_private_tags)
        try:
            dataset.save_as(target)
        except Exception as exc:
            fail(f"DICOM writing failed for {target}: {exc}")

        report["items"].append(
            {
                "input": path.name,
                "output": target.name,
                "slide_id": slide_id,
                "pseudonym": pseudonym,
                "status": "success",
            }
        )
        log(f"{slide_id}: pseudonymized {path.name} -> {target.name}")

    # TODO: Add THS / OMI pseudonymization integration.
    # TODO: Add external pseudonymization service integration.
    report_path = OUTPUT_DIR / "pseudonymization_report.json"
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
