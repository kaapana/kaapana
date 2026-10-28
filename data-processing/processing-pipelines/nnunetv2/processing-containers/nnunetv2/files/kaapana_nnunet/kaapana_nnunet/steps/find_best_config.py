"""nnUNetv2_find_best_configuration over trained models of one dataset.

Uses every selected configuration whose folds are all published. The outputs (inference_information.json,
inference_instructions.txt, crossval results and postprocessing per model, ensembles) are published as the
unit best.<id> of results/<Dataset>/, where <id> names the compared models.
"""

import hashlib
import json

from kaapana_nnunet import layout
from kaapana_nnunet.context import Context, StepError, provenance, run_nnunet, sync_dropdowns
from kaapana_nnunet.store import NotPublished


def run(ctx: Context):
    selected_model = ctx.selection()  # any model of the dataset, its trainer and plans are the defaults
    dataset, model_name = selected_model.split("/")[1:3]
    trainer, plans, configuration = model_name.split("__")
    trainers = (ctx.get("trainers") or trainer).replace(",", " ").split()
    plans_list = (ctx.get("plans") or plans).replace(",", " ").split()
    configurations = ctx.get("configurations") or [configuration]
    folds = [str(f) for f in (ctx.get("folds") or ["0", "1", "2", "3", "4"])]
    if "all" in folds:
        raise StepError("nnUNetv2_find_best_configuration needs cross-validation folds (0-4), not 'all'.")

    ctx.prepare()
    store = ctx.store
    results = layout.pod_dir("results") / dataset
    used, skipped = [], []
    for tr in trainers:
        for pl in plans_list:
            for cfg in configurations:
                prefix = layout.results_prefix(dataset, tr, pl, cfg)
                have = {m["unit"] for m in store.list_markers(prefix)}
                missing = [f for f in folds if layout.fold_unit(f) not in have]
                if missing:
                    skipped.append(f"{tr}__{pl}__{cfg} (folds {', '.join(missing)} missing)")
                    continue
                for f in folds:
                    store.fetch(prefix, results / layout.model_folder_name(tr, pl, cfg), unit=layout.fold_unit(f))
                used.append((tr, pl, cfg))
    if skipped:
        print("Not compared:\n  " + "\n  ".join(skipped), flush=True)
    if not used:
        raise StepError("No model has all requested folds trained.")
    # nnU-Net reads the plans and the reference segmentations (gt_segmentations) from nnUNet_preprocessed
    pre_prefix = layout.preprocessed_prefix(dataset)
    pre_dir = layout.pod_dir("preprocessed") / dataset
    data_identifiers = []
    for pl in dict.fromkeys(p for _, p, _ in used):
        try:
            marker = store.fetch(pre_prefix, pre_dir, unit=layout.plans_unit(pl))
        except NotPublished:
            raise StepError(f"The plans {pl} of {dataset} are no longer in nnunet/{pre_prefix}/.")
        data_identifiers += [marker["meta"]["configurations"].get(c) for t, p, c in used if p == pl]
    # gt_segmentations is the same in every data unit; take one that was trained on, so it is published
    data_identifier = next((d for d in data_identifiers if store.is_published(pre_prefix, layout.data_unit(d))), None)
    if data_identifier is None:
        raise StepError(f"No preprocessed data of the compared models is left in nnunet/{pre_prefix}/.")
    if not (pre_dir / "gt_segmentations").is_dir():
        store.fetch(
            pre_prefix,
            pre_dir,
            unit=layout.data_unit(data_identifier),
            include=lambda rel: rel.startswith("gt_segmentations/"),
        )

    dataset_id, _ = layout.parse_dataset_name(dataset)
    before = {p for p in results.rglob("*") if p.is_file()}
    args = ["nnUNetv2_find_best_configuration", str(dataset_id), "-f", *folds]
    args += ["-c", *dict.fromkeys(c for _, _, c in used)]
    args += ["-tr", *dict.fromkeys(t for t, _, _ in used)]
    args += ["-p", *dict.fromkeys(p for _, p, _ in used)]
    if ctx.flag("disable_ensembling"):
        args.append("--disable_ensembling")
    if ctx.get("np"):
        args += ["-np", str(ctx.get("np"))]
    run_nnunet(
        args,
        hint="If .npz files are missing: ensembling needs the folds trained with --npz, or disable ensembling.",
    )

    new = sorted(p.relative_to(results).as_posix() for p in results.rglob("*") if p.is_file() and p not in before)
    key = hashlib.sha1(json.dumps(sorted(used)).encode()).hexdigest()[:8]
    store.publish(
        results,
        f"results/{dataset}",
        new,
        unit=f"best.{key}",
        meta=provenance(ctx, dataset=dataset, models=["__".join(m) for m in used], folds=folds),
        overwrite=True,
    )
    print((results / "inference_instructions.txt").read_text(), flush=True)
    sync_dropdowns(ctx)
