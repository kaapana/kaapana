"""nnUNetv2_predict_from_modelfolder on DICOM images; results go back to the PACS as DICOM SEG.

Inputs are rebuilt with the channel rules stored in the model (kaapana.json): every selected image series is
one case, the channel 'segmented' is that series, other channels are found in its study by their rules.
"""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import SimpleITK as sitk

from kaapana_nnunet import channels as ch
from kaapana_nnunet import dicom, sources
from kaapana_nnunet.pacs import check_aetitle, send_to_pacs
from kaapana_nnunet.context import Context, StepError, run_nnunet
from kaapana_nnunet.sources import MODALITY, SERIES, STUDY

logger = logging.getLogger(__name__)


def model_channels(kaapana: dict, dataset_json: dict) -> tuple[list[ch.Channel], bool]:
    if kaapana:
        rows = kaapana["channels"]
        if len(rows) == 1 and not rows[0].get("name") and rows[0].get("rule", ch.SEGMENTED) == ch.SEGMENTED:
            rows = []  # the default: one channel, the segmented series
        return ch.parse_channels(rows), kaapana.get("resample_to_first_channel", True)
    if len(dataset_json["channel_names"]) != 1:
        raise StepError(
            "This model was trained on an uploaded raw dataset with several channels and has no channel rules, "
            "so its inputs cannot be found in DICOM."
        )
    return ch.parse_channels([]), True


def postprocess(ctx: Context, dataset: str, model_name: str, folds: list[str], model_dir, out_dir):
    """Apply the postprocessing that nnUNetv2_find_best_configuration determined for exactly these folds."""
    if not ctx.flag("apply_postprocessing", True):
        return out_dir
    pkl = f"{model_name}/crossval_results_folds_{'_'.join(sorted(folds))}/postprocessing.pkl"
    best = [
        m
        for m in ctx.store.list_markers(f"results/{dataset}")
        if m["prefix"] == f"results/{dataset}"
        and (m["unit"] or "").startswith("best.")
        and any(e["path"] == pkl for e in m["marker"]["files"])
    ]
    if not best:
        print(
            "No postprocessing determined for this model and these folds (run nnunetv2-find-best-config).", flush=True
        )
        return out_dir
    newest = max(best, key=lambda m: m["marker"]["created"])
    local = ctx.scratch / "best"
    ctx.store.fetch(f"results/{dataset}", local, unit=newest["unit"], include=lambda p: p == pkl)
    pp_dir = out_dir.parent / "output_postprocessed"
    run_nnunet(
        [
            "nnUNetv2_apply_postprocessing",
            "-i",
            str(out_dir),
            "-o",
            str(pp_dir),
            "-pp_pkl_file",
            str(local / pkl),
            "-plans_json",
            str(model_dir / "plans.json"),
            "-dataset_json",
            str(model_dir / "dataset.json"),
        ]
    )
    return pp_dir


def run(ctx: Context):
    model_prefix = ctx.selection()
    dataset, model_name = model_prefix.split("/")[1:3]
    aetitle = ctx.get("aetitle") or "nnunet-seg"
    check_aetitle(aetitle)
    ctx.prepare()
    store = ctx.store
    model_dir = ctx.scratch / "model" / model_name

    available = sorted(
        m["unit"][len("fold_") :] for m in store.list_markers(model_prefix) if (m["unit"] or "").startswith("fold_")
    )
    folds = [str(f) for f in (ctx.get("folds") or available)]
    missing = sorted(set(folds) - set(available))
    if missing:
        raise StepError(f"Folds {', '.join(missing)} are not trained. Trained: {', '.join(available) or 'none'}.")
    for fold in folds:
        store.fetch(model_prefix, model_dir, unit=f"fold_{fold}")
    dataset_json = json.loads((model_dir / "dataset.json").read_text())
    plans = json.loads((model_dir / "plans.json").read_text())
    configuration = model_name.split("__")[2]
    if plans["configurations"][configuration].get("previous_stage"):
        raise StepError("Cascade models (3d_cascade_fullres) cannot be used for prediction yet.")
    kaapana = json.loads((model_dir / "kaapana.json").read_text()) if (model_dir / "kaapana.json").is_file() else {}
    channels, resample = model_channels(kaapana, dataset_json)
    label_names = {v: k for k, v in dataset_json["labels"].items() if v}

    identifiers = ctx.identifiers
    if not identifiers:
        raise StepError("The selected Kaapana dataset is empty.")
    meta = sources.Metadata(ctx.project["opensearch_index"])
    series_meta = meta.series(identifiers)
    images = {u: m for u, m in series_meta.items() if m.get(MODALITY) not in dicom.SEG_MODALITIES}
    if not images:
        raise StepError("The dataset contains no image series (only segmentations).")
    download = sources.downloader(ctx.scratch / "dicom")
    in_dir, out_dir, seg_dir = ctx.scratch / "input", ctx.scratch / "output", ctx.scratch / "seg"
    in_dir.mkdir(parents=True, exist_ok=True)

    # with a 'segmented' channel every selected image series is a case; otherwise every study is one,
    # and the SEG goes onto the series of channel 0
    per_series = any(c.is_segmented for c in channels)
    cases, problems, seen_studies = {}, [], set()
    for uid, m in sorted(images.items()):
        if not per_series and m[STUDY] in seen_studies:
            continue
        seen_studies.add(m[STUDY])
        try:
            picked = ch.assign(channels, uid, meta.study_series(m[STUDY]), lambda x: x[SERIES], ch.describe_series)
        except ch.RuleError as e:
            problems.append(f"series {uid}: {e}")
            continue
        cases[f"case_{len(cases):04d}"] = {
            "series": uid if per_series else picked[0],
            "study": m[STUDY],
            "channels": picked,
        }

    def convert(item):
        case_id, case = item
        imgs = [dicom.read_image_series(download(u, case["study"])) for u in case["channels"]]
        for c in range(1, len(imgs)):
            if not dicom.same_geometry(imgs[c], imgs[0]):
                if not resample:
                    raise dicom.ConversionError(f"channel {c} has a different geometry than channel 0")
                imgs[c] = dicom.resample_to(imgs[c], imgs[0])
        for c, img in enumerate(imgs):
            sitk.WriteImage(img, str(in_dir / f"{case_id}_{c:04d}.nii.gz"), useCompression=True)

    with ThreadPoolExecutor(4) as pool:
        for (case_id, case), future in [(i, pool.submit(convert, i)) for i in cases.items()]:
            try:
                future.result()
            except (dicom.ConversionError, RuntimeError) as e:
                problems.append(f"series {case['series']}: {e}")
                cases.pop(case_id)
    if problems:
        print(f"Problems ({len(problems)}):\n" + "\n".join(problems), flush=True)
    if not cases:
        raise StepError("No series could be prepared for prediction.")

    args = ["nnUNetv2_predict_from_modelfolder", "-i", str(in_dir), "-o", str(out_dir), "-m", str(model_dir)]
    args += ["-f", *folds, "--disable_progress_bar"]
    for key, flag in (("checkpoint", "-chk"), ("step_size", "-step_size"), ("npp", "-npp"), ("nps", "-nps")):
        if ctx.get(key) is not None:
            args += [flag, str(ctx.get(key))]
    for key, flag in (("disable_tta", "--disable_tta"), ("not_on_device", "--not_on_device"), ("verbose", "--verbose")):
        if ctx.flag(key):
            args.append(flag)
    if os.environ.get("NNUNET_DEVICE"):
        args += ["-device", os.environ["NNUNET_DEVICE"]]
    run_nnunet(args)
    out_dir = postprocess(ctx, dataset, model_name, folds, model_dir, out_dir)

    description = ctx.get("seg_description") or f"nnU-Net {dataset}"
    written = 0
    for case_id, case in cases.items():
        prediction = sitk.ReadImage(str(out_dir / f"{case_id}.nii.gz"))
        image, files = dicom.read_image_series(download(case["series"], case["study"]), with_files=True)
        segmented = case["channels"].index(case["series"]) if case["series"] in case["channels"] else 0
        if segmented != 0 or not dicom.same_geometry(prediction, image):
            prediction = dicom.resample_to(prediction, image, label=True)
        labels = sitk.GetArrayFromImage(prediction).astype(np.uint8)
        try:
            if dicom.write_seg(labels, files, label_names, seg_dir / case_id / "seg.dcm", description, model_name):
                written += 1
            else:
                print(f"series {case['series']}: nothing segmented, no SEG written", flush=True)
        except dicom.ConversionError as e:
            problems.append(f"series {case['series']}: {e}")
    if written:
        send_to_pacs(ctx, seg_dir, aetitle)
    print(f"{written} segmentation(s) sent to the PACS.", flush=True)
    if problems and not ctx.flag("skip_invalid_cases"):
        raise StepError(f"{len(problems)} series could not be processed:\n" + "\n".join(problems))


if __name__ == "__main__":
    from kaapana_nnunet.context import main

    main(run)
