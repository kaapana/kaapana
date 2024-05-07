import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

from attr import dataclass
import pytest


from .utils import mock_modules, PLUGIN_DIR, DICOM_TAG_DICT
from .generator import (
    generate_ct,
    generate_rtstruct,
    generate_seg,
    NOW,
    PLUS_DATETIME,
    MINUS_DATETIME,
)

sys.path.insert(0, str(PLUGIN_DIR))
mock_modules()
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


def __init__(self, *args, **kwargs):
    pass


@dataclass
class Dag:
    run_id: str


AIRFLOW_WORKFLOW_DIR = "tests/airflow_workflow_dir"
OPERATOR_IN_DIR = "operator_in_dir"
OPERATOR_OUT_DIR = "operator_out_dir"
BATCH_NAME = "batch_name"
DAG_RUN_ID = "dag_run_id"
RUN_DIR = Path(AIRFLOW_WORKFLOW_DIR) / DAG_RUN_ID


@pytest.fixture
def op(request):
    # Default parameters
    marker = request.node.get_closest_marker("params")
    if marker is None:
        params = {}
    else:
        params = marker.args[0]

    os.environ["DICT_PATH"] = str(DICOM_TAG_DICT)

    dag = Dag(run_id=DAG_RUN_ID)

    def mock_decorator_function(func):
        def wrapper(*args, **kwargs):
            result = func(dag_run=dag, *args, **kwargs)
            return result

        return wrapper

    mock1 = patch.object(KaapanaPythonBaseOperator, "__init__", __init__)
    # mock2 = patch.object(SkipMixin, "__init__", __init__)
    # mock3 = patch.object(PythonOperator, "__init__", __init__)
    mock4 = patch(
        "kaapana.operators.HelperCaching.cache_operator_output",
        mock_decorator_function,
    )
    # with mock1, mock2, mock3, mock4:
    with mock1, mock4:
        from kaapana.operators.LocalDcm2JsonOperator import LocalDcm2JsonOperator

        op = LocalDcm2JsonOperator(dag="", exit_on_error=True)
        op.airflow_workflow_dir = AIRFLOW_WORKFLOW_DIR
        op.operator_in_dir = OPERATOR_IN_DIR
        op.operator_out_dir = OPERATOR_OUT_DIR
        op.batch_name = BATCH_NAME

        op.manage_cache = "ignore"

        ct_path = RUN_DIR / BATCH_NAME / "ct" / OPERATOR_IN_DIR / "ct.dcm"
        seg_path = RUN_DIR / BATCH_NAME / "seg" / OPERATOR_IN_DIR / "seg.dcm"
        rtst_path = RUN_DIR / BATCH_NAME / "rtst" / OPERATOR_IN_DIR / "rtst.dcm"

        generate_ct(ct_path, params)
        generate_seg(seg_path, params)
        generate_rtstruct(rtst_path, params)

        return op


def read_ct():
    ct_path = RUN_DIR / BATCH_NAME / "ct" / OPERATOR_OUT_DIR / "ct.json"
    with open(ct_path, "r") as fp:
        return json.load(fp)


def read_seg():
    seg_path = RUN_DIR / BATCH_NAME / "seg" / OPERATOR_OUT_DIR / "seg.json"
    with open(seg_path, "r") as fp:
        return json.load(fp)


def read_rtst():
    rtst_path = RUN_DIR / BATCH_NAME / "rtst" / OPERATOR_OUT_DIR / "rtst.json"
    with open(rtst_path, "r") as fp:
        return json.load(fp)


# Standard CT
def test_standard_ct(op):
    op.start()
    json_ct = read_ct()

    assert (
        json_ct["00100010 PatientName_keyword_alphabetic"]
        == 'SAIC_Pfenning_Prop++luss"2"^1.Messung'
    )


# PatientAge
@pytest.mark.params(
    {
        "PatientAge": "004Y",
        "PatientBirthDate": "",
    },
)
def test_patient_age(op):
    op.start()
    json_ct = read_ct()
    # timestamp = json_ct["0008002A AcquisitionDateTime_datetime"]
    # patient_birthdate = json_ct["00100030 PatientBirthDate_date"]
    derived_age = json_ct["00000000 DerivedPatientAge_integer"]

    assert derived_age == 4


# DATETIMES
@pytest.mark.params(
    {"AcquisitionDateTime": NOW.strftime("%Y%m%d%H")},
)
def test_unparsable_datetime(op):
    with pytest.raises(ValueError):
        op.start()


@pytest.mark.params(
    {"AcquisitionDateTime": MINUS_DATETIME.strftime("%Y%m%d%H%M%S.%f%z")},
)
def test_minus_timezone_datetime(op):
    with pytest.raises(ValueError):
        op.start()


@pytest.mark.params(
    {"AcquisitionDateTime": PLUS_DATETIME.strftime("%Y%m%d%H%M%S.%f%z")},
)
def test_plus_timezone_datetime(op):
    with pytest.raises(ValueError):
        op.start()


@pytest.mark.parametrize(
    "input_age, expected_output",
    [
        ("0100Y", 100),
        ("0034Y", 34),
        ("0015Y", 15),
        ("0000Y", 0),
        ("0001M", 0),
        ("0006W", 0),
        ("0366D", 1),
    ],
)
def test_process_age_string(input_age, expected_output):
    from kaapana.operators.LocalDcm2JsonOperator import process_age_string

    age = process_age_string(input_age)
    assert age == expected_output


@pytest.mark.parametrize(
    "vr, value_str, expected_value, expected_type",
    [
        # Keyword
        ("AE", "value", "value", "keyword"),
        ("AE", "value", "value", "keyword"),
        ("AS", "value", "value", "keyword"),
        ("AT", "value", "value", "keyword"),
        ("CS", "value", "value", "keyword"),
        ("LO", "value", "value", "keyword"),
        ("LT", "value", "value", "keyword"),
        ("OB", "value", "value", "keyword"),
        ("OW", "value", "value", "keyword"),
        ("SH", "value", "value", "keyword"),
        ("ST", "value", "value", "keyword"),
        ("UC", "value", "value", "keyword"),
        ("UI", "value", "value", "keyword"),
        ("UN", "value", "value", "keyword"),
        ("UT", "value", "value", "keyword"),
        # DCM_DATETIME_FORMAT = "%Y%m%d%H%M%S.%f"
        # KAAPANA_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
        (
            "DT",
            "20240101120000",
            # From UTC to Berlin
            "2024-01-01 11:00:00.000000",
            "datetime",
        ),
        (
            "DT",
            "20240101",
            "2024-01-01 00:00:00.000000",
            "datetime",
        ),
        # DCM_TIME_FORMAT = "%H%M%S.%f"
        # KAAPANA_TIME_FORMAT = "%H:%M:%S.%f"
        (
            "TM",
            "120000",
            # Not from UTC to Berlin
            "12:00:00.000000",
            "time",
        ),
        (
            "TM",
            "000000",
            "00:00:00.000000",
            "time",
        ),
        # DCM_DATE_FORMAT = "%Y%m%d"
        # KAAPANA_DATE_FORMAT = "%Y-%m-%d"
        (
            "DA",
            "20240505",
            "2024-05-05",
            "date",
        ),
        (
            "DA",
            "20240101",
            "2024-01-01",
            "date",
        ),
        # Float
        ("DS", 0.001, 0.001, "float"),
        ("FL", 0.001, 0.001, "float"),
        ("FD", 2, 2.0, "float"),
        ("OD", "0.001", 0.001, "float"),
        ("OF", 0.001, 0.001, "float"),
        # Int
        ("IS", 0, 0, "integer"),
        ("SL", "1", 1, "integer"),
        ("SS", "0.5", 0, "integer"),
        ("UL", "0.sd5", "0.sd5", "integer"),
        ("US", 0.001, 0, "integer"),
    ],
)
def test_normalize_tag(op, vr, value_str, expected_value, expected_type):
    new_tag = "00000000 TestTag"
    metadata = op._normalize_tag(new_tag, vr, value_str, {})
    if expected_type is None:
        assert f"{new_tag}_{expected_type}" not in metadata.keys()

    assert metadata[f"{new_tag}_{expected_type}"] == expected_value

    if expected_type == "keyword":
        isinstance(metadata[f"{new_tag}_{expected_type}"], str)
    elif expected_type == "datetime":
        isinstance(metadata[f"{new_tag}_{expected_type}"], str)
    elif expected_type == "date":
        isinstance(metadata[f"{new_tag}_{expected_type}"], str)
    elif expected_type == "time":
        isinstance(metadata[f"{new_tag}_{expected_type}"], str)
    elif expected_type == "float":
        isinstance(metadata[f"{new_tag}_{expected_type}"], float)
    elif expected_type == "integer":
        isinstance(metadata[f"{new_tag}_{expected_type}"], int)


@pytest.mark.parametrize(
    "vr, value_str, expected_value, expected_type",
    [
        # Person Name
        (
            "PN",
            {"Alphabetic": "My\\{Int\\}io+n-12345678900-==][]' @!@##$%^&*()_"},
            "My\\{Int\\}io+n-12345678900-==][]' @!@##$%^&*()_",
            "keyword_alphabetic",
        ),
        (
            "PN",
            {"Ideographic": "FamilyName"},
            "FamilyName",
            "keyword_ideographic",
        ),
        (
            "PN",
            {"Phonetic": "FamilyName"},
            "FamilyName",
            "keyword_phonetic",
        ),
    ],
)
def test_normalize_tag_personname(op, vr, value_str, expected_value, expected_type):
    new_tag = "00000000 TestTag"
    metadata = op._normalize_tag(new_tag, vr, value_str, {})
    assert metadata[f"{new_tag}_{expected_type}"] == expected_value


# @pytest.mark.parametrize(
#     "vr, value_str, expected_value, expected_type",
#     [
#         # Sequence
#         ("SQ", [], [], "object"),
#     ],
# )
# def test_normalize_tag_sequence(
#     op, vr, value_str, expected_value, expected_type
# ):
#     new_tag = "00000000 TestTag"
#     metadata = op._normalize_tag(new_tag, vr, value_str, {})
#     assert metadata[f"{new_tag}_{expected_type}"] == expected_value
