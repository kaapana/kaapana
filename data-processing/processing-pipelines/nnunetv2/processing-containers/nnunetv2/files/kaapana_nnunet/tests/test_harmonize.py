import numpy as np
import pytest
from kaapana_nnunet import harmonize as hz

SHAPE = (6, 20, 20)
SPACING = (1.0, 1.0, 5.0)  # x, y, z in mm: 5 mm³ per voxel


def box(z0, z1, y0, y1, x0, x1):
    mask = np.zeros(SHAPE, bool)
    mask[z0:z1, y0:y1, x0:x1] = True
    return mask


ORGAN = box(1, 5, 2, 18, 2, 18)  # 4*16*16 = 1024 voxels
LESION = box(2, 4, 8, 12, 8, 12)  # 2*4*4 = 32 voxels, inside the organ
SOURCES = {
    "a": hz.Source("a", "SEG #300 manual (a)", "Liver manual", "Dr A", "20240101120000"),
    "b": hz.Source("b", "SEG #900 nnU-Net Liver (b)", "nnU-Net Liver", "", "20240301120000"),
}


def run(rows, segments, inner_wins=False):
    return hz.apply(hz.parse_rules(rows), segments, SOURCES, SPACING, inner_wins)


def only(out):
    (mask,) = out.segments.values()
    return mask


def seg(name, mask, source="a"):
    return hz.Segment(name, mask, source)


def test_overlap_without_rule_refuses():
    out = run([], [seg("Liver", ORGAN), seg("Tumour", LESION)])
    (problem,) = out.problems
    assert problem.startswith("OVERLAP: 'Liver' and 'Tumour' share 32 voxels (160 mm³)")
    assert "priority' (Tumour, Liver)" in problem


def test_priority_earlier_wins_regardless_of_row_order():
    out = run([{"rule": "priority", "segments": "Tumour, Liver"}], [seg("Liver", ORGAN), seg("Tumour", LESION)])
    assert not out.problems
    assert out.segments["Tumour"].sum() == 32 and out.segments["Liver"].sum() == 1024 - 32
    assert not (out.segments["Tumour"] & out.segments["Liver"]).any()


def test_inner_wins_is_opt_in_and_reported():
    out = run([], [seg("Liver", ORGAN), seg("Tumour", LESION)], inner_wins=True)
    assert not out.problems and out.segments["Liver"].sum() == 1024 - 32
    assert any("inner wins: 'Tumour' lies 100% inside 'Liver'" in n for n in out.notes)
    # partial overlap is not containment: still refused
    half = box(0, 2, 0, 20, 0, 20)  # 2*20*20 = 800 voxels, only z=1 overlaps the organ
    out = run([], [seg("Liver", ORGAN), seg("Body", half)], inner_wins=True)
    assert out.problems and "needs 80%" in out.problems[0]


def test_rename_wildcards_and_case_unite_segments():
    rows = [{"rule": "rename", "segments": "Leber*, LIVER", "target": "liver"}]
    out = run(rows, [seg("Leber_1", box(1, 2, 2, 4, 2, 4)), seg("LIVER", box(3, 4, 2, 4, 2, 4))])
    assert list(out.segments) == ["liver"] and out.segments["liver"].sum() == 8
    assert 1 in out.applied


def test_drop_keep_only_combine_cut_out():
    pz, tz = box(1, 5, 2, 10, 2, 18), box(1, 5, 10, 18, 2, 18)
    rows = [
        {"rule": "cut_out", "segments": "lesion", "target": "prostate"},  # row order does not matter
        {"rule": "combine", "segments": "pz, tz", "target": "prostate"},
        {"rule": "keep_only", "segments": "pz, tz, lesion"},
    ]
    out = run(rows, [seg("PZ", pz), seg("TZ", tz), seg("lesion", LESION), seg("urethra", box(0, 1, 0, 1, 0, 1))])
    assert sorted(out.segments) == ["lesion", "prostate"]
    assert out.segments["prostate"].sum() == 1024 - 32 and not out.problems
    assert out.changed_mm3[3] == 5 and out.changed_mm3[1] == 32 * 5
    assert any("'prostate' lost" in n for n in out.notes) is False  # 3% loss is below the warning


def test_remove_specks_in_mm3():
    speck = box(0, 1, 0, 1, 0, 1)  # 1 voxel = 5 mm³
    out = run([{"rule": "remove_specks", "segments": "*", "value": "10"}], [seg("Liver", ORGAN | speck)])
    assert out.segments["Liver"].sum() == 1024 and out.changed_mm3[1] == 5


def test_choose_version():
    rows = [{"rule": "choose_version", "segments": "liver", "value": "newest"}]
    two = [seg("Liver", ORGAN, "a"), seg("liver", LESION, "b")]
    out = run(rows, two)
    assert only(out).sum() == 32 and list(out.segments) == ["liver"]  # b is newer, its spelling
    out = run([{"rule": "choose_version", "segments": "liver", "value": "description ~ manual"}], two)
    assert only(out).sum() == 1024
    out = run([{"rule": "choose_version", "segments": "*", "value": "author ~ ."}], two)
    assert only(out).sum() == 1024  # only a has an author
    out = run([{"rule": "choose_version", "segments": "*", "value": "union"}], two)
    assert only(out).sum() == 1024
    out = run([], two)
    assert "comes from 2 segmentation objects" in out.problems[0]
    out = run([{"rule": "choose_version", "segments": "*", "value": "description ~ liver"}], two)
    assert "matches 2 of them" in out.problems[0]


def test_large_loss_and_swallowed_segments_are_reported():
    rows = [{"rule": "priority", "segments": "Liver, Tumour"}]
    out = run(rows, [seg("Liver", ORGAN), seg("Tumour", LESION)])
    assert "Tumour" not in out.segments
    assert any("'Tumour' lost 100% of its voxels (now empty)" in n for n in out.notes)


@pytest.mark.parametrize(
    "row,message",
    [
        ({"rule": "rename", "segments": "a"}, "second name"),
        ({"rule": "nonsense", "segments": "a"}, "unknown rule"),
        ({"rule": "choose_version", "segments": "a", "value": "best"}, "'Keep' must be newest"),
        ({"rule": "remove_specks", "segments": "*", "value": "-1"}, "volume in mm³"),
        ({"rule": "priority", "segments": "a"}, "at least two"),
        ({"rule": "drop", "segments": ""}, "'Segments' is empty"),
    ],
)
def test_rule_validation(row, message):
    with pytest.raises(hz.RuleError, match=message):
        hz.parse_rules([row])


def test_deterministic_and_hash_ignores_row_order():
    a = [{"rule": "drop", "segments": "x"}, {"rule": "rename", "segments": "y", "target": "z"}]
    assert hz.rules_hash(hz.parse_rules(a)) == hz.rules_hash(hz.parse_rules(a[::-1]))
    one = run(a, [seg("y", ORGAN), seg("x", LESION)])
    two = run(a[::-1], [seg("x", LESION), seg("y", ORGAN)])
    assert one.segments.keys() == two.segments.keys()
    assert all((one.segments[k] == two.segments[k]).all() for k in one.segments)
