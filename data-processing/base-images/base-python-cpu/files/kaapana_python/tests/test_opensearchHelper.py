import sys
from pathlib import Path


sys.path.insert(
    0,
    str(Path(__file__).resolve().parent / "../"),
)
from tests.mock_modules import mock_modules

mock_modules()

from kaapanapy.Clients.OpensearchHelper import sanitize_field_name, combine_tags


def test_sanitize_field_name():
    camelCase = "00180015 BodyPartExamined_keyword.keyword"
    assert sanitize_field_name(camelCase) == "Body Part Examined"


def test_combine_tags():
    tags = ["tag1", "tag2", "tag3"]
    tags2add = ["new_tag1", "new_tag2"]
    tags2delete = ["tag2", "new_tag1"]
    original_tags = ["tag1", "original_tag1"]

    assert sorted(
        combine_tags(
            tags=tags,
            tags2add=tags2add,
            tags2delete=tags2delete,
            original_tags=original_tags,
        )
    ) == sorted(["tag1", "tag3", "new_tag1", "new_tag2", "original_tag1"])
