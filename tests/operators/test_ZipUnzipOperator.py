import os
import subprocess
import sys
import zipfile

from .utils import KAAPANA_DIR

PROCESS_PY = (
    KAAPANA_DIR
    / "data-processing/kaapana-plugin/processing-containers/zip-unzip/files/process.py"
)


def test_batch_unzip_skips_corrupt_archive(tmp_path):
    # Batch-level layout the upload DAGs produce: WORKFLOW_DIR/<in_dir>/*.zip
    in_dir = tmp_path / "dicoms"
    in_dir.mkdir()
    with zipfile.ZipFile(in_dir / "good.zip", "w") as z:
        z.writestr("a.dcm", b"dicom")
    (in_dir / "bad.zip").write_bytes(b"not a zip archive")

    result = _run_batch_unzip(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "unzipped" / "a.dcm").read_bytes() == b"dicom"


def test_batch_unzip_falls_back_to_batch_element_dirs(tmp_path):
    # Archives placed per batch element: WORKFLOW_DIR/batch/<element>/<in_dir>/*.zip
    in_dir = tmp_path / "batch" / "element" / "dicoms"
    in_dir.mkdir(parents=True)
    with zipfile.ZipFile(in_dir / "good.zip", "w") as z:
        z.writestr("a.dcm", b"dicom")

    result = _run_batch_unzip(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "unzipped" / "a.dcm").read_bytes() == b"dicom"


def _run_batch_unzip(workflow_dir):
    env = {
        **os.environ,
        "WORKFLOW_DIR": str(workflow_dir),
        "BATCH_NAME": "batch",
        "OPERATOR_IN_DIR": "dicoms",
        "OPERATOR_OUT_DIR": "unzipped",
        "MODE": "unzip",
        "BATCH_LEVEL": "True",
    }
    return subprocess.run(
        [sys.executable, str(PROCESS_PY)], env=env, capture_output=True, text=True
    )
