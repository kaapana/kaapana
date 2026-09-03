import sys
from unittest.mock import MagicMock

from .generator import generate_ct
from .utils import KAAPANA_DIR, mock_modules

# The delete-from-pacs processing container is a plain script, so import it from its
# files/ directory with kaapanapy mocked the same way the operator tests do.
CONTAINER_DIR = (
    KAAPANA_DIR / "data-processing/kaapana-plugin/processing-containers/delete-from-pacs/files"
)
sys.path.insert(0, str(CONTAINER_DIR))
mock_modules()
sys.modules["kaapanapy.helper.HelperDcmWeb"] = MagicMock()
from start import DeleteFromPacsOperator  # noqa: E402


def test_dicom_input_resolves_study_to_delete(tmp_path):
    """Raw DICOM input without metadata json must still produce a PACS delete request."""
    study_uid = "1.2.826.0.1.3680043.8.498.1"
    generate_ct(
        tmp_path / "batch" / "series" / "in" / "series.dcm",
        {"StudyInstanceUID": study_uid},
    )

    op = DeleteFromPacsOperator(delete_complete_study=True)
    op.conf = {"project_form": {"id": "project-1"}, "workflow_form": {}}
    op.workflow_dir, op.batch_name, op.operator_in_dir = str(tmp_path), "batch", "in"
    op.dcmweb_helper = MagicMock()

    op.start()

    op.dcmweb_helper.delete_study.assert_called_once_with(
        project_id="project-1", study_uid=study_uid
    )
