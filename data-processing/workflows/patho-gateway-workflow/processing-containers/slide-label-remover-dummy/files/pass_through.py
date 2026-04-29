#!/usr/bin/env python3
import json
import shutil
import sys
from pathlib import Path

INPUT_DIR = Path("/kaapana/input/dicom")
OUTPUT_DIR = Path("/kaapana/output/dicom-label-removed")


def log(message):
    print(message, flush=True)


def fail(message):
    raise RuntimeError(message)


def is_dicom(path):
    try:
        import pydicom

        return pydicom.misc.is_dicom(path)
    except Exception:
        with path.open("rb") as f:
            f.seek(128)
            return f.read(4) == b"DICM"


def move_with_copy_fallback(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(source), str(target))
        return "moved"
    except Exception as move_exc:
        log(f"Move failed for {source}: {move_exc}. Trying copy fallback.")
        shutil.copy2(source, target)
        if target.exists() and target.stat().st_size == source.stat().st_size:
            source.unlink()
            return "copied"
        fail(f"Copy fallback failed for {source}; target is missing or incomplete.")


def copy_sidecar_reports():
    for source in INPUT_DIR.glob("*.json"):
        shutil.copy2(source, OUTPUT_DIR / source.name)


def main():
    log(f"Input directory: {INPUT_DIR}")
    log(f"Output directory: {OUTPUT_DIR}")
    if not INPUT_DIR.is_dir():
        fail(f"Input directory does not exist: {INPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(path for path in INPUT_DIR.rglob("*") if path.is_file() and path.suffix.lower() != ".json")
    log(f"Number of files found: {len(files)}")
    if not files:
        fail(f"No DICOM input files found in {INPUT_DIR}.")

    items = []
    for path in files:
        if not is_dicom(path):
            fail(f"Unsupported input file format for {path}. Expected DICOM.")
        target = OUTPUT_DIR / path.name
        action = move_with_copy_fallback(path, target)
        items.append({"input": path.name, "output": target.name, "action": action, "status": "success"})
        log(f"{path.name}: passed through via {action}")

    copy_sidecar_reports()
    report = {
        "status": "skipped",
        "reason": "Label removal strategy is not finalized yet",
        "items": items,
    }
    report_path = OUTPUT_DIR / "label_removal_report.json"
    with report_path.open("w") as f:
        json.dump(report, f, indent=2)
    log(f"Number of files written: {len(items)}")
    log(f"Final report path: {report_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
