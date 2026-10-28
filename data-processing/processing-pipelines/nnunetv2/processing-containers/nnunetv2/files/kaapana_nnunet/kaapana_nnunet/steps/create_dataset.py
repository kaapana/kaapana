"""Kaapana dataset (images + SEG/RTSTRUCT) -> nnUNet_raw/DatasetXXX_Name in S3.

One case = one segmented image series; all segmentation objects of the dataset that reference it are merged.
"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor

import SimpleITK as sitk

from kaapana_nnunet import channels as ch
from kaapana_nnunet import dicom, layout, sources
from kaapana_nnunet.context import Context, StepError, main, provenance, sync_dropdowns
from kaapana_nnunet.sources import MODALITY, SERIES, STUDY
from kaapana_nnunet.store import AlreadyPublished

logger = logging.getLogger(__name__)


def _label_table(rows: list[dict], found: set[str], ignore_unlisted: bool) -> tuple[dict[str, int], dict[str, int]]:
    """Form rows [{name, aliases}] -> ({nnU-Net label name: value}, {segment name (lower): value}).
    Without rows every distinct segment name becomes its own label (sorted)."""
    if not rows:
        names = sorted(found, key=str.lower)
        labels = {n: i + 1 for i, n in enumerate(names)}
        return labels, {n.lower(): v for n, v in labels.items()}
    labels, lookup, errors = {}, {}, []
    for i, row in enumerate(rows):
        name = re.sub(r"\s+", "_", str(row.get("name") or "").strip())
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
            + ". Add them (as label or alias) or enable 'Ignore segments not in the label table'."
        )
    if errors:
        raise StepError("Label table problems:\n" + "\n".join(errors))
    return labels, lookup


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
        raise StepError(f"Channel table problems:\n{e}")

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
        ds = dicom.read_segmentation_object(download(uid, m[STUDY]))
        return uid, m[STUDY], ds

    with ThreadPoolExecutor(8) as pool:
        for uid, study_uid, ds in pool.map(load_seg, seg_uids):
            ref = dicom.referenced_series_uid(ds)
            if not ref:
                problems.append(f"{ds.Modality} {uid}: does not reference an image series")
                continue
            case = cases.setdefault(ref, {"study": study_uid, "segmentations": []})
            case["segmentations"].append((uid, ds))

    found_names = set()
    for case in cases.values():
        for _, ds in case["segmentations"]:
            if ds.Modality == "SEG":
                found_names.update(str(s.SegmentLabel).strip() for s in ds.SegmentSequence)
            else:
                found_names.update(str(r.ROIName).strip() for r in ds.StructureSetROISequence)
    labels, lookup = _label_table(label_rows, found_names, ignore_unlisted)

    # 2. channels per case
    for ref_uid, case in sorted(cases.items()):
        try:
            study = meta.study_series(case["study"])
            case["channels"] = ch.assign(channels, ref_uid, study, lambda m: m[SERIES])
            by_uid = {m[SERIES]: m for m in study}
            case["modalities"] = [by_uid.get(u, {}).get(MODALITY, "") for u in case["channels"]]
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
            ctx, name, cases, channels, labels, lookup, problems, download, check_only, resample, skip_invalid
        )
    except BaseException:
        if not check_only and not ctx.store.is_published(layout.raw_prefix(name)):
            layout.release_dataset(ctx.store, name)
        raise


def _convert_and_publish(
    ctx, name, cases, channels, labels, lookup, problems, download, check_only, resample, skip_invalid
):
    raw = ctx.scratch / "raw" / name
    (raw / "imagesTr").mkdir(parents=True, exist_ok=True)
    (raw / "labelsTr").mkdir(parents=True, exist_ok=True)
    valid = [(ref, c) for ref, c in sorted(cases.items()) if not c.get("invalid")]
    case_ids = {ref: f"{name.split('_', 1)[1]}_{n:04d}" for n, (ref, _) in enumerate(valid)}
    overlaps_total: dict[int, int] = {}

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
                        "(enable 'Resample channels to the first channel')"
                    )
                images[c] = dicom.resample_to(image, first)
        segmented = images[case["channels"].index(ref_uid)] if ref_uid in case["channels"] else None
        if segmented is None:
            segmented = dicom.read_image_series(download(ref_uid, case["study"]))
        masks = {}
        for _, ds in case["segmentations"]:
            for seg_name, mask in dicom.segment_masks(ds, segmented).items():
                if seg_name.lower() not in lookup:
                    continue  # ignore_unlisted (otherwise the label table already failed)
                key = f"{seg_name}#{len(masks)}"
                masks[key] = mask
        label_of = {k: lookup[k.rsplit("#", 1)[0].lower()] for k in masks}
        label_image, overlaps = dicom.labelmap(masks, label_of, segmented)
        if not dicom.same_geometry(label_image, first):
            label_image = dicom.resample_to(label_image, first, label=True)
        for c, image in enumerate(images):
            sitk.WriteImage(image, str(raw / "imagesTr" / f"{case_id}_{c:04d}.nii.gz"), useCompression=True)
        sitk.WriteImage(label_image, str(raw / "labelsTr" / f"{case_id}.nii.gz"), useCompression=True)
        return ref_uid, overlaps

    converted = {}
    with ThreadPoolExecutor(4) as pool:
        futures = {pool.submit(convert, item): item for item in valid}
        for future, (ref_uid, case) in futures.items():
            try:
                _, overlaps = future.result()
                converted[ref_uid] = case
                for k, v in overlaps.items():
                    overlaps_total[k] = overlaps_total.get(k, 0) + v
            except (dicom.ConversionError, RuntimeError) as e:
                problems.append(f"series {ref_uid}: {e}")

    report = [
        f"Dataset:   {name}",
        f"Cases:     {len(converted)} of {len(cases)} segmented series",
        "Channels:  " + ", ".join(f"{i}: {c.name or 'segmented series'} ({c.rule})" for i, c in enumerate(channels)),
        "Labels:    " + ", ".join(f"{v}: {n}" for n, v in labels.items()),
    ]
    if overlaps_total:
        inv = {v: n for n, v in labels.items()}
        report.append(
            "Overlaps:  "
            + ", ".join(f"{inv[v]} overwritten in {n} voxels by a higher label" for v, n in overlaps_total.items())
        )
    if problems:
        report += ["", f"Problems ({len(problems)}):", *problems]
    print("\n".join(report), flush=True)

    if problems and not (skip_invalid and converted):
        raise StepError(
            f"{len(problems)} problem(s), see the list above. Fix the data or the rules, "
            "or enable 'Skip invalid cases'." + (" Nothing was uploaded." if not check_only else "")
        )
    if check_only:
        print("\nCheck only: nothing was uploaded.", flush=True)
        return

    modalities = [sorted({c["modalities"][i] for c in converted.values()}) for i in range(len(channels))]
    dataset_json = {
        "channel_names": {str(i): ch.nnunet_channel_name(c, set(modalities[i])) for i, c in enumerate(channels)},
        "labels": {"background": 0, **labels},
        "numTraining": len(converted),
        "file_ending": ".nii.gz",
        "name": name,
        "description": ctx.get("description", ""),
    }
    (raw / "dataset.json").write_text(json.dumps(dataset_json, indent=2))
    # what prediction needs to rebuild the inputs, and where every case came from
    kaapana_json = {
        "channels": [
            {"name": c.name, "rule": c.rule, "normalization": c.normalization, "modalities": modalities[i]}
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
                "segmentations": [uid for uid, _ in c["segmentations"]],
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
    print(f"\nPublished s3://{ctx.bucket}/nnunet/{layout.raw_prefix(name)}/", flush=True)
    sync_dropdowns(ctx)


if __name__ == "__main__":
    main(run)
