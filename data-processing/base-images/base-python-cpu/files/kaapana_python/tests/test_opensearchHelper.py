import sys
from pathlib import Path


sys.path.insert(
    0,
    str(Path(__file__).resolve().parent / "../"),
)
from tests.mock_modules import mock_modules

mock_modules()

from kaapanapy.Clients.OpensearchHelper import sanitize_field_name


def test_sanitize_field_name():
    camelCase = "00180015 BodyPartExamined_keyword.keyword"
    assert sanitize_field_name(camelCase) == "Body Part Examined"
