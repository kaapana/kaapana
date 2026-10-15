import importlib.util
import sys
from unittest.mock import MagicMock, patch

from .generator import generate_ct
from .utils import KAAPANA_DIR

SCRIPT = (
    KAAPANA_DIR
    / "data-processing/kaapana-plugin/processing-containers/get-ref-series/files"
    / "get-ref-series.py"
)
KAAPANAPY = [
    "kaapanapy",
    "kaapanapy.helper",
    "kaapanapy.helper.HelperDcmWeb",
    "kaapanapy.helper.HelperOpensearch",
]


def load_get_ref_series():
    spec = importlib.util.spec_from_file_location("get_ref_series", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {name: MagicMock() for name in KAAPANAPY}):
        spec.loader.exec_module(module)
    return module


def test_patient_uid_prepares_series_of_other_studies(tmp_path):
    dcm = tmp_path / "batch" / "1.1.1" / "in" / "ct.dcm"
    generate_ct(
        dcm,
        {"PatientID": "P-1", "StudyInstanceUID": "1.1", "SeriesInstanceUID": "1.1.1"},
    )
    op = load_get_ref_series().GetRefSeriesOperator("idx", search_policy="patient_uid")
    op.os_helper.execute_opensearch_query.return_value = [
        {
            "_source": {
                "0020000E SeriesInstanceUID_keyword": series,
                "0020000D StudyInstanceUID_keyword": study,
            }
        }
        for series, study in [("1.1.1", "1.1"), ("2.2.2", "2.2")]
    ]

    series = op.prepare_download_function(str(dcm), str(tmp_path), "batch", "out")

    op.os_helper.execute_opensearch_query.assert_called_once_with(
        index="idx", query={"term": {"00100020 PatientID_keyword.keyword": "P-1"}}
    )
    assert [(s.series_instance_uid, s.study_instance_uid) for s in series] == [
        ("2.2.2", "2.2")
    ]
