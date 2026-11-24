"""
Workflows stored before private user datasets (#1643) - all of a platform migrated
from 0.6.x - hold data_form.dataset_name as the dataset's plain name. The workflow
list, whose schema expects the object, answered 500 for every project holding one.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.workflows import schemas  # noqa: E402


def test_a_plain_dataset_name_is_a_project_dataset():
    assert schemas.dataset_name_object("mig-a-ct") == {
        "name": "mig-a-ct",
        "access_level": "project",
    }


def test_an_object_and_none_stay_as_they_are():
    current = {"name": "mine", "username": "u", "access_level": "private"}
    assert schemas.dataset_name_object(current) is current
    assert schemas.dataset_name_object(None) is None


def test_the_workflow_list_item_accepts_a_plain_dataset_name():
    validators = schemas.WorkflowListItem.__pydantic_decorators__.field_validators
    assert validators["legacy_dataset_name"].info.fields == ("dataset_name",)
    assert schemas.WorkflowListItem.legacy_dataset_name("mig-a-ct") == {
        "name": "mig-a-ct",
        "access_level": "project",
    }
