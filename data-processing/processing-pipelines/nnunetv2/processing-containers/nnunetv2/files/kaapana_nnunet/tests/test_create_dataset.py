from collections import Counter

import pytest
from kaapana_nnunet.context import StepError
from kaapana_nnunet.steps.create_dataset import _label_table


def test_auto_labels_merge_case_and_spacing():
    found = Counter({"Liver": 5, "liver": 1, "Left Kidney": 2, "left_kidney": 1})
    labels, lookup, merged = _label_table([], found, False)
    assert labels == {"Left_Kidney": 1, "Liver": 2}
    assert lookup["liver"] == lookup["liver"] == 2 and lookup["left kidney"] == lookup["left_kidney"] == 1
    assert merged == {"Left_Kidney": ["left_kidney"], "Liver": ["liver"]}


@pytest.mark.parametrize("name", ["Segment_1", "segment 2", "ROI-3", "1"])
def test_auto_labels_refuse_generic_names(name):
    with pytest.raises(StepError, match="do not say which structure"):
        _label_table([], Counter({"Liver": 1, name: 1}), False)


def test_label_rows_order_aliases_and_unlisted():
    rows = [{"name": "Prostate"}, {"name": "Lesion", "aliases": "Tumour, tumor"}]
    labels, lookup, _ = _label_table(rows, Counter({"prostate": 1, "Tumour": 1}), False)
    assert labels == {"Prostate": 1, "Lesion": 2} and lookup["tumour"] == 2
    with pytest.raises(StepError, match="not in the label table: Bladder"):
        _label_table(rows, Counter({"Prostate": 1, "Bladder": 1}), False)
    assert _label_table(rows, Counter({"Prostate": 1, "Bladder": 1}), True)[0] == labels
