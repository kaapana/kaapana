import os
import runpy
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

CONVERT_ITK2DCM = (
    Path(__file__).resolve().parents[2]
    / "data-processing/kaapana-plugin/processing-containers/itk2dcm/files"
    / "convert-itk2dcm.py"
)


def test_itk2dcm_converts_input_written_per_batch_element(tmp_path):
    nifti = tmp_path / "batch" / "series-1" / "nifti-in" / "case0.nii.gz"
    nifti.parent.mkdir(parents=True)
    nifti.touch()
    env = {
        "WORKFLOW_DIR": str(tmp_path),
        "BATCH_NAME": "batch",
        "OPERATOR_IN_DIR": "nifti-in",
        "OPERATOR_OUT_DIR": "dcm-out",
    }
    sitk = MagicMock()
    with patch.dict(os.environ, env), patch.dict(sys.modules, {"SimpleITK": sitk}):
        runpy.run_path(str(CONVERT_ITK2DCM), run_name="__main__")

    sitk.ReadImage.assert_called_once_with(str(nifti))
