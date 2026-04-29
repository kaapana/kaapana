#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

INPUT_DIR = Path("/kaapana/input/wsi")
OUTPUT_DIR = Path("/kaapana/output/dicom")
REPORT_NAME = "conversion_report.json"


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
    for name in ("manifest.json",):
        source = INPUT_DIR / name
        if source.is_file():
            shutil.copy2(source, OUTPUT_DIR / name)


def convert_svs_to_dicom(source):
    command = os.getenv("WSIDICOMIZER_COMMAND", "wsidicomizer")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        cmd = [command, "-i", str(source), "-o", str(tmp_dir)]
        log(f"{source.name}: running {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            log(result.stdout)
        if result.stderr:
            log(result.stderr)
        if result.returncode != 0:
            fail(f"SVS conversion failed for {source.name} with exit code {result.returncode}.")

        dicom_files = sorted(path for path in tmp_dir.rglob("*") if path.is_file())
        if not dicom_files:
            fail(f"SVS conversion for {source.name} did not produce any files.")

        outputs = []
        for index, dicom_file in enumerate(dicom_files, start=1):
            suffix = ".dcm"
            if len(dicom_files) == 1:
                target = OUTPUT_DIR / f"{source.stem}{suffix}"
            else:
                target = OUTPUT_DIR / f"{source.stem}_{index:04d}{suffix}"
            shutil.move(str(dicom_file), str(target))
            outputs.append(target)
        return outputs


def main():
    log(f"Input directory: {INPUT_DIR}")
    log(f"Output directory: {OUTPUT_DIR}")
    if not INPUT_DIR.is_dir():
        fail(f"Input directory does not exist: {INPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(
        path for path in INPUT_DIR.rglob("*") if path.is_file() and path.suffix.lower() != ".json"
    )
    log(f"Number of files found: {len(files)}")
    if not files:
        fail(f"No WSI input files found in {INPUT_DIR}.")

    report = {"items": []}
    written = 0
    for path in files:
        suffix = path.suffix.lower()
        if suffix == ".svs":
            outputs = convert_svs_to_dicom(path)
            written += len(outputs)
            report["items"].append(
                {
                    "input": path.name,
                    "output": outputs[0].name if len(outputs) == 1 else [p.name for p in outputs],
                    "action": "converted",
                    "status": "success",
                }
            )
            log(f"{path.name}: converted to {len(outputs)} DICOM file(s)")
        elif is_dicom(path):
            target = OUTPUT_DIR / path.name
            action = move_with_copy_fallback(path, target)
            written += 1
            report["items"].append(
                {
                    "input": path.name,
                    "output": target.name,
                    "action": action,
                    "status": "success",
                }
            )
            log(f"{path.name}: {action} to {target}")
        else:
            fail(f"Unsupported input file format for {path}. Expected SVS or DICOM.")

    copy_sidecar_reports()
    report_path = OUTPUT_DIR / REPORT_NAME
    with report_path.open("w") as f:
        json.dump(report, f, indent=2)
    log(f"Number of files written: {written}")
    log(f"Final report path: {report_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
