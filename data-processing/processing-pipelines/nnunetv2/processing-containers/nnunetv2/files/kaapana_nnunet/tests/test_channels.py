import pytest
from kaapana_nnunet import channels as ch

STUDY = [
    {
        "0020000E SeriesInstanceUID_keyword": "t2",
        "0008103E SeriesDescription_keyword": "AX T2 TSE",
        "00080060 Modality_keyword": "MR",
        "00000000 Tags_keyword": ["train"],
    },
    {
        "0020000E SeriesInstanceUID_keyword": "adc",
        "0008103E SeriesDescription_keyword": "ep2d_diff ADC",
        "00080060 Modality_keyword": "MR",
        "00000000 Tags_keyword": [],
    },
    {
        "0020000E SeriesInstanceUID_keyword": "dwi",
        "0008103E SeriesDescription_keyword": "ep2d_diff TRACEW",
        "00080060 Modality_keyword": "MR",
    },
]
UID = lambda m: m["0020000E SeriesInstanceUID_keyword"]  # noqa: E731


def test_default_is_segmented_series():
    channels = ch.parse_channels([])
    assert ch.assign(channels, "t2", STUDY, UID) == ["t2"]


def test_rules_pick_one_series_each():
    channels = ch.parse_channels(
        [
            {"name": "T2", "rule": "segmented"},
            {"name": "ADC", "rule": "SeriesDescription ~ adc"},
            {"name": "DWI", "rule": "SeriesDescription ~ diff & SeriesDescription ~ trace"},
        ]
    )
    assert ch.assign(channels, "t2", STUDY, UID) == ["t2", "adc", "dwi"]


def test_tags_and_negation():
    channels = ch.parse_channels(
        [
            {"name": "X", "rule": "Tags = TRAIN"},
            {"name": "Y", "rule": "Modality = MR & Tags != train & SeriesDescription ~ adc"},
        ]
    )
    assert ch.assign(channels, "t2", STUDY, UID) == ["t2", "adc"]


def test_ambiguous_and_missing_rules_fail():
    channels = ch.parse_channels(
        [{"name": "A", "rule": "SeriesDescription ~ ep2d"}, {"name": "B", "rule": "Modality = CT"}]
    )
    with pytest.raises(ch.RuleError) as e:
        ch.assign(channels, "t2", STUDY, UID)
    assert "matches 2 series" in str(e.value) and "matches 0 series" in str(e.value)


@pytest.mark.parametrize(
    "rows",
    [
        [{"name": "", "rule": "Modality = MR"}],
        [{"name": "a", "rule": "Modality MR"}],
        [{"name": "a", "rule": "SeriesDescription ~ ("}],
        [{"name": "a", "rule": "segmented"}, {"name": "b", "rule": "segmented"}],
        [{"name": "a", "rule": "segmented"}, {"name": "A", "rule": "Modality = MR"}],
        [{"name": "a", "rule": "segmented", "normalization": "minmax"}],
    ],
)
def test_invalid_tables(rows):
    with pytest.raises(ch.RuleError):
        ch.parse_channels(rows)


def test_normalization_names():
    c = ch.Channel(name="T2", rule="segmented")
    assert ch.nnunet_channel_name(c, {"MR"}) == "T2"
    assert ch.nnunet_channel_name(ch.Channel(name="", rule="segmented"), {"CT"}) == "CT"
    assert ch.nnunet_channel_name(ch.Channel(name="CT", rule="segmented"), {"MR"}) == "zscore"
    assert ch.nnunet_channel_name(ch.Channel(name="x", rule="segmented", normalization="noNorm"), {"CT"}) == "noNorm"
