import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# The container's modules are flat files next to start.py, not a package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "files"))

from dciodvfy import DCIodValidator  # noqa: E402


def test_hanging_dciodvfy_is_killed_and_reported():
    process = MagicMock()

    def communicate(timeout=None):
        if process.kill.called:
            return b"", b""  # reaping the killed process
        if timeout is None:
            pytest.fail("dciodvfy awaited without a bound; a stuck file hangs forever")
        raise subprocess.TimeoutExpired(cmd="dciodvfy", timeout=timeout)

    process.communicate.side_effect = communicate
    with patch("dciodvfy.subprocess.Popen", return_value=process):
        errors, warnings = DCIodValidator().validate_dicom("/data/slice.dcm")

    assert process.kill.called
    assert warnings == []
    assert len(errors) == 1 and errors[0].type == "Error"
