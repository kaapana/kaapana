"""nnUNetv2_extract_fingerprint / nnUNetv2_plan_experiment / nnUNetv2_preprocess, each optional.

Form values map 1:1 to nnU-Net arguments; an empty field means "nnU-Net's default" (the flag is not passed).
Outputs are published per unit (see layout): fingerprint, plans.<plans>, data.<data_identifier>.
The data unit also carries gt_segmentations/ and splits_final.json, so a training needs nothing else.
"""

import json
import logging
from pathlib import Path

from kaapana_nnunet import layout, pretrained
from kaapana_nnunet.context import Context, StepError, main, provenance, run_nnunet, sync_dropdowns
from kaapana_nnunet.gpu import gpu_memory_gb
from kaapana_nnunet.store import NotPublished, sha256_file

logger = logging.getLogger(__name__)

INTEGRITY_HINT = (
    "If this is the dataset integrity check: nnU-Net found an inconsistency in the raw dataset, e.g. label values "
    "missing from dataset.json, images and labels with different geometry, or NaN values. The lines above say "
    "which case. Fix the source data and create the dataset again."
)
FIXED_FILES = {"dataset.json", "dataset_fingerprint.json", "splits_final.json"}


def _plans_files(folder: Path) -> dict[str, float]:
    return {p.name: p.stat().st_mtime for p in folder.glob("*.json") if p.name not in FIXED_FILES}


def _logging_flags(ctx: Context) -> list[str]:
    return ["--no_pbar"] + (["--verbose"] if ctx.flag("verbose") else [])


def run(ctx: Context):
    dataset = ctx.selection()
    dataset_id, _ = layout.parse_dataset_name(dataset)
    do_fingerprint = ctx.flag("run_fingerprint", True)
    do_plan = ctx.flag("run_planning", True)
    do_preprocess = ctx.flag("run_preprocessing", True)
    if not (do_fingerprint or do_plan or do_preprocess):
        raise StepError("Select at least one of fingerprint, planning and preprocessing.")

    ctx.prepare()
    store = ctx.store
    pre_prefix = layout.preprocessed_prefix(dataset)
    pre_dir = layout.pod_dir("preprocessed") / dataset
    pre_dir.mkdir(parents=True, exist_ok=True)

    try:
        store.fetch(layout.raw_prefix(dataset), layout.pod_dir("raw") / dataset)
    except NotPublished:
        raise StepError(f"The raw dataset {dataset} does not exist (any more) in this project.")

    # ---------- fingerprint ----------
    fingerprint_new = False
    have_fingerprint = store.is_published(pre_prefix, "fingerprint")
    if do_fingerprint and (ctx.flag("clean") or not have_fingerprint):
        args = ["nnUNetv2_extract_fingerprint", "-d", str(dataset_id), *_logging_flags(ctx)]
        if ctx.advanced("fingerprint_extractor"):
            args += ["-fpe", ctx.advanced("fingerprint_extractor")]
        if ctx.advanced("np_fingerprint"):
            args += ["-np", str(ctx.advanced("np_fingerprint"))]
        if ctx.flag("verify_dataset_integrity", True):
            args.append("--verify_dataset_integrity")
        args.append("--clean")  # the pod starts empty; a published fingerprint was handled above
        run_nnunet(args, hint=INTEGRITY_HINT)
        fingerprint_new = True
    elif have_fingerprint:
        if do_fingerprint:
            print("Fingerprint already exists, keeping it (set 'clean' to extract it again).", flush=True)
        store.fetch(pre_prefix, pre_dir, unit="fingerprint")
    else:
        raise StepError(f"{dataset} has no fingerprint yet. Enable 'Extract fingerprint'.")

    if fingerprint_new:
        store.publish(
            pre_dir,
            pre_prefix,
            ["dataset_fingerprint.json"],  # dataset.json is copied by the planning step
            unit="fingerprint",
            meta=provenance(ctx, dataset=dataset),
            overwrite=True,
        )

    # ---------- planning ----------
    before = _plans_files(pre_dir)
    if do_plan:
        args = ["nnUNetv2_plan_experiment", "-d", str(dataset_id), *_logging_flags(ctx)]
        planner = ctx.get("planner_class") or ctx.get("planner")
        if planner:
            args += ["-pl", planner]
        for key, flag in (
            ("gpu_memory_target", "-gpu_memory_target"),
            ("preprocessor_name", "-preprocessor_name"),
            ("overwrite_plans_name", "-overwrite_plans_name"),
        ):
            if ctx.advanced(key):
                args += [flag, str(ctx.advanced(key))]
        if ctx.advanced("overwrite_target_spacing"):
            args += [
                "-overwrite_target_spacing",
                *str(ctx.advanced("overwrite_target_spacing")).replace(",", " ").split(),
            ]
        run_nnunet(args)
        after = _plans_files(pre_dir)
        written = [n for n, t in after.items() if before.get(n) != t]
        if len(written) != 1:
            raise StepError(f"Expected nnU-Net to write one plans file, found {written or 'none'} in {pre_dir}.")
        plans_name = written[0][: -len(".json")]
        plans = json.loads((pre_dir / written[0]).read_text())
        configurations = {c: v.get("data_identifier") for c, v in plans["configurations"].items()}
        unit = layout.plans_unit(plans_name)
        stale = []
        if store.is_published(pre_prefix, unit):
            old = store.read_marker(pre_prefix, unit)
            new_sha = sha256_file(pre_dir / written[0])
            if any(e["path"] == written[0] and e["sha256"] == new_sha for e in old["files"]):
                print(f"Plans {plans_name} are unchanged.", flush=True)
            else:
                stale = sorted(set(old["meta"].get("configurations", {}).values()) - {None})
        store.publish(
            pre_dir,
            pre_prefix,
            ["dataset.json", written[0]],
            unit=unit,
            meta=provenance(
                ctx,
                dataset=dataset,
                plans=plans_name,
                configurations=configurations,
                gpu_memory_gb=gpu_memory_gb(plans, ctx.advanced("gpu_memory_target")),
            ),
            overwrite=True,
        )
        for data_identifier in stale:
            if store.is_published(pre_prefix, layout.data_unit(data_identifier)):
                logger.warning("plans changed: removing outdated preprocessed data %s", data_identifier)
                store.delete(pre_prefix, layout.data_unit(data_identifier))
    else:
        plans_name = ctx.get("plans_name") or "nnUNetPlans"
        try:
            store.fetch(pre_prefix, pre_dir, unit=layout.plans_unit(plans_name))
        except NotPublished:
            raise StepError(f"{dataset} has no plans '{plans_name}'. Enable 'Plan experiment' or fix the plans name.")
        plans = json.loads((pre_dir / f"{plans_name}.json").read_text())
        configurations = {c: v.get("data_identifier") for c, v in plans["configurations"].items()}

    print(f"Plans: {plans_name}, configurations: {', '.join(configurations)}", flush=True)

    # ---------- preprocessing ----------
    if do_preprocess:
        selected = ctx.get("configurations") or ["2d", "3d_fullres", "3d_lowres"]
        missing = [c for c in selected if c not in configurations]
        selected = [c for c in selected if c in configurations]
        if missing:
            print(f"Not in the plans, skipped (as nnU-Net does): {', '.join(missing)}", flush=True)
        if not selected:
            raise StepError("None of the selected configurations exists in the plans.")
        args = ["nnUNetv2_preprocess", "-d", str(dataset_id), "-plans_name", plans_name, "-c", *selected]
        args += _logging_flags(ctx)
        nps = ctx.advanced("np_preprocessing")
        if nps:
            args += ["-np", *str(nps).replace(",", " ").split()]
        run_nnunet(args)

        _write_default_splits(pre_dir, configurations[selected[0]])
        for data_identifier in dict.fromkeys(configurations[c] for c in selected):
            store.publish(
                pre_dir,
                pre_prefix,
                [data_identifier, "gt_segmentations", "splits_final.json", "dataset.json"],
                unit=layout.data_unit(data_identifier),
                meta=provenance(
                    ctx,
                    dataset=dataset,
                    plans=plans_name,
                    configurations=[c for c in selected if configurations[c] == data_identifier],
                ),
                overwrite=True,
            )
            print(f"Published preprocessed data {data_identifier}", flush=True)

    if ctx.get("pretrained_uploaded") or ctx.get("pretrained"):
        _adapt_to_pretrained(ctx, dataset, dataset_id, pre_dir, pre_prefix, plans_name)

    sync_dropdowns(ctx)


def _adapt_to_pretrained(ctx: Context, dataset, dataset_id, pre_dir: Path, pre_prefix: str, base_plans: str):
    """nnFoundation / nnssl finetuning: adapt the plans to the pretrained checkpoint and preprocess for it
    (nnUNetv2_preprocess_like_nnssl, or nnUNetv2_plan_like_dynamic for the dynamic adaptation)."""
    store = ctx.store
    name = ctx.get("pretrained_uploaded") or ctx.get("pretrained")
    try:
        checkpoint = pretrained.fetch(store, name)
    except pretrained.PretrainedError as e:
        raise StepError(str(e))
    mode = ctx.get("adaptation_mode")  # empty: nnU-Net's default (default_nnunet)
    pretraining_name = ctx.get("pretraining_name") or name.replace("/", "_")
    before = _plans_files(pre_dir)
    if mode == "dynamic":
        args = ["nnUNetv2_plan_like_dynamic", "-d", str(dataset_id), "-n", pretraining_name, "-pc", str(checkpoint)]
        args += ["-pl", base_plans]
    else:
        args = ["nnUNetv2_preprocess_like_nnssl", "-d", str(dataset_id), "-n", pretraining_name, "-pc", str(checkpoint)]
        if mode:
            args += ["-am", mode]
        if ctx.get("override_spacing"):
            args += ["-os", *str(ctx.get("override_spacing")).replace(",", " ").split()]
    if ctx.get("np_pretrained"):
        args += ["-np", str(ctx.get("np_pretrained"))]
    if ctx.flag("verbose"):
        args.append("--verbose")
    run_nnunet(
        args, hint="The adaptation needs normal plans with a 3d_fullres configuration (enable 'Plan experiment')."
    )

    written = [n for n, t in _plans_files(pre_dir).items() if before.get(n) != t]
    if len(written) != 1:
        raise StepError(f"Expected one adapted plans file, found {written or 'none'}.")
    plans_name = written[0][: -len(".json")]
    plans = json.loads((pre_dir / written[0]).read_text())
    data_identifier = plans["configurations"]["3d_fullres"]["data_identifier"]
    # nnU-Net's adaptation does not build the foreground sampling location store that training needs
    run_nnunet(
        ["nnUNetv2_extract_sampling_locations", "-d", str(dataset_id), "-plans_name", plans_name, "-c", "3d_fullres"]
    )
    _write_default_splits(pre_dir, data_identifier)
    meta = provenance(ctx, dataset=dataset, plans=plans_name, pretrained=name, base_plans=base_plans)
    store.publish(
        pre_dir,
        pre_prefix,
        ["dataset.json", written[0]],
        unit=layout.plans_unit(plans_name),
        meta={**meta, "configurations": {"3d_fullres": data_identifier}, "gpu_memory_gb": gpu_memory_gb(plans)},
        overwrite=True,
    )
    store.publish(
        pre_dir,
        pre_prefix,
        [data_identifier, "gt_segmentations", "splits_final.json", "dataset.json"],
        unit=layout.data_unit(data_identifier),
        meta={**meta, "configurations": ["3d_fullres"]},
        overwrite=True,
    )
    print(f"Published {plans_name} (pretrained: {name}); train it with nnunetv2-train.", flush=True)


def _write_default_splits(pre_dir: Path, data_identifier: str):
    """Exactly what nnUNetTrainer.do_split would create, written once here so that parallel folds never race."""
    from nnunetv2.utilities.crossval_split import generate_crossval_split

    splits_file = pre_dir / "splits_final.json"
    if splits_file.is_file():
        return
    folder = pre_dir / data_identifier
    identifiers = sorted(p.name[: -len(".b2nd")] for p in folder.glob("*.b2nd") if not p.name.endswith("_seg.b2nd"))
    splits = generate_crossval_split(identifiers, seed=12345, n_splits=5)
    splits_file.write_text(json.dumps(splits, indent=4))


if __name__ == "__main__":
    main(run)
