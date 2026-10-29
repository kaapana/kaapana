"""Kaapana dataset (images + SEG/RTSTRUCT) -> nnUNet_raw/DatasetXXX_Name in S3.

One case = one segmented image series; all segmentation objects of the dataset that reference it are merged.
Nothing is guessed silently: overlapping segments (nnU-Net needs one label per voxel), a channel with mixed or
unknown modality without a normalization, or one label coming from two segmentation objects of a series fail
the run.
"""

import json
import logging
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import SimpleITK as sitk

from kaapana_nnunet import channels as ch
from kaapana_nnunet import dicom, layout, sources
from kaapana_nnunet.context import Context, StepError, main, provenance, sync_dropdowns
from kaapana_nnunet.sources import MODALITY, SERIES, STUDY
from kaapana_nnunet.store import AlreadyPublished

logger = logging.getLogger(__name__)

DOCS = "/docs/user_guide/extensions/nnunet.html"
HELP = {
    "channels": f"{DOCS}#nnunetv2-create-channels",
    "labels": f"{DOCS}#nnunetv2-create-labels",
    "report": f"{DOCS}#reading-the-report",
    "splits": f"{DOCS}#nnunetv2-splits",
}
# segment names that say nothing about the structure: they can mean different things in different cases
GENERIC_NAME = re.compile(r"^(segment|label|roi|structure|mask)?[\s_-]*\d+$", re.IGNORECASE)


def _clean(name: str) -> str:
    return re.sub(r"\s+", "_", name.strip())


def _label_table(
    rows: list[dict], found: Counter, ignore_unlisted: bool
) -> tuple[dict[str, int], dict[str, int], dict[str, list[str]]]:
    """Form rows [{name, aliases}] -> ({nnU-Net label name: value}, {segment name (lower): value},
    {label name: other spellings merged into it}).

    Without rows every segment name becomes its own label, sorted. Names that differ only in case or spacing
    are one label (the most frequent spelling names it); generic names like 'Segment_1' are refused."""
    if not rows:
        groups: dict[str, Counter] = {}
        for name, n in found.items():
            groups.setdefault(_clean(name).lower(), Counter())[name] += n
        generic = sorted(n for g in groups.values() for n in g if GENERIC_NAME.match(n))
        if generic:
            raise StepError(
                "Label problems:\nthese segment names do not say which structure they are, and can mean "
                f"different structures in different cases: {', '.join(generic)}. Rename the segments, or list "
                f"the labels in Advanced -> Labels. See {HELP['labels']}"
            )
        labels, lookup, merged = {}, {}, {}
        for value, key in enumerate(sorted(groups), start=1):
            spellings = sorted(groups[key], key=lambda s: (-groups[key][s], s))
            label = _clean(spellings[0])
            labels[label] = value
            lookup.update({s.lower(): value for s in spellings})
            if len(spellings) > 1:
                merged[label] = spellings[1:]
        return labels, lookup, merged
    labels, lookup, errors = {}, {}, []
    for i, row in enumerate(rows):
        name = _clean(str(row.get("name") or ""))
        if not name:
            errors.append(f"label row {i + 1}: a name is required")
            continue
        value = i + 1
        labels[name] = value
        aliases = [a.strip() for a in str(row.get("aliases") or "").split(",") if a.strip()]
        for alias in [str(row.get("name")).strip(), *aliases]:
            if lookup.get(alias.lower(), value) != value:
                errors.append(f"'{alias}' is listed for two labels")
            lookup[alias.lower()] = value
    unlisted = sorted(n for n in found if n.lower() not in lookup)
    if unlisted and not ignore_unlisted:
        errors.append(
            "these segment names are in the data but not in the label table: "
            + ", ".join(unlisted)
            + ". Add them (as label or in 'Also matches') or enable 'Ignore segments not in the label table'."
        )
    if errors:
        raise StepError("Label table problems:\n" + "\n".join(errors) + f"\nSee {HELP['labels']}")
    return labels, lookup, {}


def _segment_names(ds) -> list[str]:
    if ds.Modality == "SEG":
        return [str(s.SegmentLabel).strip() for s in ds.SegmentSequence]
    return [str(r.ROIName).strip() for r in ds.StructureSetROISequence]


def _description(meta: dict) -> str:
    values = ch.field_values(meta, "SeriesDescription")
    return str(values[0]) if values else "(no description)"


def run(ctx: Context):
    dataset_title = ctx.require("dataset_name")
    channel_rows = ctx.get("channels") or []
    label_rows = ctx.get("labels") or []
    check_only = ctx.flag("check_only")
    resample = ctx.flag("resample_to_first_channel", True)
    ignore_unlisted = ctx.flag("ignore_unlisted_segments")
    skip_invalid = ctx.flag("skip_invalid_cases")

    try:
        channels = ch.parse_channels(channel_rows)
    except ch.RuleError as e:
        raise StepError(f"Channel table problems:\n{e}\nSee {HELP['channels']}")

    identifiers = ctx.identifiers
    if not identifiers:
        raise StepError("The selected Kaapana dataset is empty.")
    meta = sources.Metadata(ctx.project["opensearch_index"])
    series_meta = meta.series(identifiers)
    seg_uids = [uid for uid, m in series_meta.items() if m.get(MODALITY) in dicom.SEG_MODALITIES]
    if not seg_uids:
        raise StepError(
            "The dataset contains no DICOM SEG or RTSTRUCT. Add the segmentations (not only the images) to the dataset."
        )
    logger.info("%d segmentation objects in %d series", len(seg_uids), len(identifiers))

    download = sources.downloader(ctx.scratch / "dicom")

    # 1. segmentation objects -> the image series they were drawn on
    cases: dict[str, dict] = {}
    problems: list[str] = []

    def load_seg(uid):
        m = series_meta[uid]
        try:
            return uid, m[STUDY], dicom.read_segmentation_object(download(uid, m[STUDY])), None
        except Exception as e:  # a broken object is a problem of the data, not a crash
            return uid, m[STUDY], None, e

    with ThreadPoolExecutor(8) as pool:
        for uid, study_uid, ds, error in pool.map(load_seg, seg_uids):
            seg_name = f"{series_meta[uid].get(MODALITY)} {ch.describe_series(series_meta[uid])}"
            if error is not None:
                problems.append(f"{seg_name} ({uid}): cannot be read: {error}")
                continue
            ref = dicom.referenced_series_uid(ds)
            if not ref:
                problems.append(f"{seg_name} ({uid}): does not reference an image series")
                continue
            case = cases.setdefault(ref, {"study": study_uid, "segmentations": []})
            case["segmentations"].append((uid, ds, seg_name))

    found_names = Counter(
        n for case in cases.values() for _, ds, _ in case["segmentations"] for n in _segment_names(ds)
    )
    labels, lookup, merged = _label_table(label_rows, found_names, ignore_unlisted)
    ignored = sorted(n for n in found_names if n.lower() not in lookup)

    # 2. channels per case
    for ref_uid, case in sorted(cases.items()):
        try:
            study = meta.study_series(case["study"])
            case["channels"] = ch.assign(channels, ref_uid, study, lambda m: m[SERIES], ch.describe_series)
            by_uid = {m[SERIES]: m for m in study}
            case["modalities"] = [by_uid.get(u, {}).get(MODALITY, "") for u in case["channels"]]
            case["descriptions"] = [_description(by_uid.get(u, {})) for u in case["channels"]]
            case["segmented"] = ch.describe_series(by_uid.get(ref_uid, {}))
            patient = ch.field_values(by_uid.get(ref_uid, {}), "PatientID")
            case["patient"] = str(patient[0]) if patient else None
        except ch.RuleError as e:
            problems.append(f"study {case['study']}: {e}")
            case["invalid"] = True

    # 3. convert
    try:
        if check_only:
            name = layout.dataset_name(
                int(ctx.get("dataset_id") or 0) or layout.next_free_dataset_id(ctx.store), dataset_title
            )
        else:
            name = layout.reserve_dataset(ctx.store, dataset_title, int(ctx.get("dataset_id") or 0))
    except ValueError as e:
        raise StepError(str(e))
    try:
        _convert_and_publish(
            ctx,
            name,
            cases,
            channels,
            labels,
            lookup,
            problems,
            download,
            check_only=check_only,
            resample=resample,
            skip_invalid=skip_invalid,
            merged=merged,
            ignored=ignored,
        )
    except BaseException:
        if not check_only and not ctx.store.is_published(layout.raw_prefix(name)):
            layout.release_dataset(ctx.store, name)
        raise


def _convert_and_publish(
    ctx,
    name,
    cases,
    channels,
    labels,
    lookup,
    problems,
    download,
    *,
    check_only,
    resample,
    skip_invalid,
    merged,
    ignored,
):
    raw = ctx.scratch / "raw" / name
    (raw / "imagesTr").mkdir(parents=True, exist_ok=True)
    (raw / "labelsTr").mkdir(parents=True, exist_ok=True)
    valid = [(ref, c) for ref, c in sorted(cases.items()) if not c.get("invalid")]
    case_ids = {ref: f"{name.split('_', 1)[1]}_{n:04d}" for n, (ref, _) in enumerate(valid)}
    label_name = {v: n for n, v in labels.items()}

    def convert(item):
        ref_uid, case = item
        case_id = case_ids[ref_uid]
        images = [dicom.read_image_series(download(uid, case["study"])) for uid in case["channels"]]
        first = images[0]
        for c, image in enumerate(images[1:], start=1):
            if not dicom.same_geometry(image, first):
                if not resample:
                    raise dicom.ConversionError(
                        f"channel {c} has a different geometry than channel 0 "
                        "(enable 'Resample channels onto channel 0')"
                    )
                images[c] = dicom.resample_to(image, first)
        segmented = images[case["channels"].index(ref_uid)] if ref_uid in case["channels"] else None
        if segmented is None:
            segmented = dicom.read_image_series(download(ref_uid, case["study"]))
        masks, sources_of = {}, {}
        for seg_uid, ds, seg_name in case["segmentations"]:
            for segment, mask in dicom.segment_masks(ds, segmented).items():
                if segment.lower() not in lookup:
                    continue  # ignore_unlisted (otherwise the label table already failed)
                masks[f"{segment}#{len(masks)}"] = mask
                sources_of.setdefault(lookup[segment.lower()], set()).add(f"{seg_name} ({seg_uid})")
        # e.g. a second annotator, an outdated version or an earlier nnU-Net prediction of the same series
        twice = {v: s for v, s in sources_of.items() if len(s) > 1}
        if twice:
            raise dicom.ConversionError(
                "; ".join(f"label '{label_name[v]}' comes from {len(s)} segmentation objects ({', '.join(sorted(s))})"
                          for v, s in twice.items())
                + ". Keep only one of them in the Kaapana dataset (an earlier nnU-Net prediction?), or pick one "
                "with nnunetv2-harmonize-segmentations (rule 'choose version')."
            )
        label_of = {k: lookup[k.rsplit("#", 1)[0].lower()] for k in masks}
        label_image, overlaps = dicom.labelmap(masks, label_of, segmented)
        if not dicom.same_geometry(label_image, first):
            label_image = dicom.resample_to(label_image, first, label=True)
        present = {int(v) for v in np.unique(sitk.GetArrayViewFromImage(label_image)) if v}
        if not present:
            raise dicom.ConversionError("the segmentation is empty (no voxel of any label)")
        if overlaps:
            return overlaps, present  # the run fails (see below); writing the files would be wasted
        for c, image in enumerate(images):
            sitk.WriteImage(image, str(raw / "imagesTr" / f"{case_id}_{c:04d}.nii.gz"), useCompression=True)
        sitk.WriteImage(label_image, str(raw / "labelsTr" / f"{case_id}.nii.gz"), useCompression=True)
        return overlaps, present

    converted = {}
    overlap_cases: dict[tuple[int, int], list] = {}  # (label, label) -> [voxels, [case descriptions]]
    label_cases: Counter = Counter()
    with ThreadPoolExecutor(4) as pool:
        futures = {pool.submit(convert, item): item for item in valid}
        for future, (ref_uid, case) in futures.items():
            try:
                overlaps, present = future.result()
            except (dicom.ConversionError, RuntimeError) as e:
                problems.append(f"series {case['segmented']} of study {case['study']}: {e}")
                continue
            converted[ref_uid] = case
            label_cases.update(present)
            for pair, voxels in overlaps.items():
                entry = overlap_cases.setdefault(tuple(sorted(pair)), [0, []])
                entry[0] += voxels
                entry[1].append(f"{case['segmented']} (patient {case.get('patient') or '?'})")

    # problems that concern the whole dataset: 'Skip invalid cases' cannot leave them out
    fatal: list[str] = []
    # nnU-Net needs exactly one label per voxel; deciding which segment wins would change the annotation
    for (a, b), (voxels, where) in sorted(overlap_cases.items()):
        a, b = label_name[a], label_name[b]
        fatal.append(
            f"OVERLAP: '{a}' and '{b}' overlap in {len(where)} case(s), {voxels} voxels in total: "
            + ", ".join(sorted(where)[:5])
            + (f" and {len(where) - 5} more" if len(where) > 5 else "")
            + f". Fix the segmentations so that '{a}' and '{b}' do not share voxels, e.g. with "
            "nnunetv2-harmonize-segmentations (rule 'priority' or 'cut out'), or leave one of them out "
            "(Advanced -> Labels)."
        )
    if converted:
        fatal += [
            f"label '{n}' has no voxel in any case. Remove it from the label table."
            for n, v in labels.items()
            if not label_cases[v]
        ]

    modalities = [Counter(c["modalities"][i] for c in converted.values()) for i in range(len(channels))]
    channel_names = {}
    for i, c in enumerate(channels):
        channel_names[str(i)] = ch.nnunet_channel_name(c, {m for m in modalities[i] if m})
        if not c.normalization and (len(modalities[i]) > 1 or "" in modalities[i]):
            channel_names[str(i)] = "(to be chosen)"
            found = ", ".join(f"{m or 'unknown'} x{n}" for m, n in modalities[i].most_common())
            fatal.append(
                f"channel {i} ({c.name or 'segmented series'}) has mixed or unknown modalities ({found}), so the "
                "normalization cannot be chosen. Set it in Advanced -> Several images per case "
                "(one row per channel; for one channel: rule 'segmented')."
            )

    patients = {c.get("patient") for c in converted.values()}
    report = [
        f"Dataset:   {name}",
        f"Cases:     {len(converted)} of {len(cases)} segmented series, from {len(patients)} patient(s)",
    ]
    if None not in patients and len(patients) < len(converted):
        report.append(
            "           Some patients have several cases. nnU-Net's random 5-fold split can put one patient into "
            f"training and validation; consider own splits: {HELP['splits']}"
        )
    report.append("Channels:")
    for i, c in enumerate(channels):
        series = Counter(cc["descriptions"][i] for cc in converted.values())
        report.append(
            f"  {i} {c.name or 'image'} ({c.rule}): "
            + ", ".join(f"{m or 'unknown'} x{n}" for m, n in modalities[i].most_common())
            + f"; normalization {channel_names[str(i)]}; series: "
            + ", ".join(f"{d} x{n}" for d, n in series.most_common(8))
            + (" ..." if len(series) > 8 else "")
        )
    report.append("Labels:")
    for n, v in labels.items():
        also = f" (also: {', '.join(merged[n])})" if n in merged else ""
        report.append(f"  {v} {n}: in {label_cases[v]} of {len(converted)} cases{also}")
    if ignored:
        report.append("Ignored segment names: " + ", ".join(ignored))
    if fatal or problems:
        report += ["", f"Problems ({len(fatal) + len(problems)}):", *fatal, *problems]
        report += [
            "",
            f"Help: channel rules {HELP['channels']} | labels {HELP['labels']} | this report {HELP['report']}",
        ]

    if converted and not fatal:
        (raw / "dataset.json").write_text(
            json.dumps(
                {
                    "channel_names": channel_names,
                    "labels": {"background": 0, **labels},
                    "numTraining": len(converted),
                    "file_ending": ".nii.gz",
                    "name": name,
                    "description": ctx.get("description", ""),
                },
                indent=2,
            )
        )
        integrity = _verify_integrity(raw)
        if integrity:
            fatal.append(f"nnU-Net's dataset check failed: {integrity}")
            report += ["", f"Problems: nnU-Net's dataset check failed: {integrity}"]

    print("\n".join(report), flush=True)
    (raw / "report.txt").write_text("\n".join(report) + "\n")

    if overlap_cases:
        raise StepError(
            "Segments overlap. nnU-Net needs exactly one label per voxel, so overlapping segmentations cannot be "
            f"trained. Affected: {sum(len(w) for _, w in overlap_cases.values())} case(s), listed in the report "
            f"above. Fix the segmentations, e.g. with the workflow nnunetv2-harmonize-segmentations, and run again. "
            f"Nothing was uploaded. See {HELP['labels']}"
        )
    if fatal or (problems and not (skip_invalid and converted)):
        raise StepError(
            f"{len(fatal) + len(problems)} problem(s), see the report above. "
            + ("Fix the data or the form." if fatal else "Fix the data or the form, or enable 'Skip invalid cases'.")
            + (" Nothing was uploaded." if not check_only else "")
        )
    if check_only:
        print("\nCheck only: nothing was uploaded.", flush=True)
        return

    # what prediction needs to rebuild the inputs, and where every case came from
    kaapana_json = {
        "channels": [
            {"name": c.name, "rule": c.rule, "normalization": c.normalization, "modalities": sorted(modalities[i])}
            for i, c in enumerate(channels)
        ],
        "resample_to_first_channel": resample,
        "labels": [
            {"name": n, "value": v, "aliases": [a for a, x in lookup.items() if x == v]} for n, v in labels.items()
        ],
        "cases": {
            case_ids[ref]: {
                "study": c["study"],
                "channels": c["channels"],
                "segmented_series": ref,
                "segmentations": [uid for uid, _, _ in c["segmentations"]],
            }
            for ref, c in converted.items()
        },
    }
    (raw / "kaapana.json").write_text(json.dumps(kaapana_json, indent=2))

    try:
        ctx.store.publish(raw, layout.raw_prefix(name), meta=provenance(ctx, dataset=name, cases=len(converted)))
    except AlreadyPublished:
        raise StepError(f"{name} already exists in this project. Choose another dataset ID or leave it empty.")
    layout.release_dataset(ctx.store, name)
    print(f"\nPublished s3://{ctx.bucket}/nnunet/{layout.raw_prefix(name)}/ (with report.txt)", flush=True)
    sync_dropdowns(ctx)


def _verify_integrity(raw) -> str:
    """nnU-Net's own dataset check (as in plan-preprocess), so problems show up here, not one workflow later.
    Returns the error, or '' if the dataset is fine."""
    from nnunetv2.experiment_planning.verify_dataset_integrity import verify_dataset_integrity

    try:
        verify_dataset_integrity(str(raw), num_processes=4)
    except (AssertionError, RuntimeError, ValueError, FileNotFoundError) as e:
        return str(e) or type(e).__name__
    return ""


if __name__ == "__main__":
    main(run)
