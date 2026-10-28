"""nnUNetv2_train for one fold (NNUNET_FOLD). Folds of one run are separate pods that run in parallel.

While training, checkpoints and logs are published as units progress.fold_X / log.fold_X so that a
crashed or cancelled training can be continued (--c) from another run. The finished fold is the unit fold_X.
"""

import json
import logging
import os
import shutil
import threading
import time
import uuid
from pathlib import Path

from minio.error import S3Error

from kaapana_nnunet import layout, pretrained
from kaapana_nnunet.context import Context, StepError, main, provenance, run_nnunet, sync_dropdowns
from kaapana_nnunet.store import NotPublished, sha256_file

logger = logging.getLogger(__name__)

CHECKPOINTS = ("checkpoint_latest.safetensors", "checkpoint_best.safetensors")
LOG_INTERVAL_S = 600


def parse_selection(value: str) -> tuple[str, str, str]:
    try:
        dataset, plans, configuration = value.split("|")
    except ValueError:
        raise StepError(f"Unexpected selection '{value}', expected Dataset|plans|configuration.")
    return dataset, plans, configuration


def apply_custom_splits(ctx: Context, dataset: str, pre_dir: Path, fold: str) -> dict:
    """Replace splits_final.json by nnunet/splits/<dataset>/<name>.json if the form names one."""
    name = ctx.get("splits")
    if not name:
        return {"splits": "nnU-Net default (5-fold, seed 12345)"}
    name = name[: -len(".json")] if name.endswith(".json") else name
    key = ctx.store.key(f"splits/{dataset}", f"{name}.json")
    try:
        resp = ctx.store._client().get_object(ctx.store.bucket, key)
        raw = resp.read()
        resp.close()
        resp.release_conn()
    except S3Error:
        available = sorted(
            o.object_name.rsplit("/", 1)[-1]
            for o in ctx.store._client().list_objects(ctx.store.bucket, prefix=ctx.store.key(f"splits/{dataset}") + "/")
        )
        raise StepError(
            f"Splits file s3://{ctx.store.bucket}/{key} not found. "
            f"Available for {dataset}: {', '.join(available) or 'none'}. "
            'Upload a splits_final.json-style file there (a list of {"train": [...], "val": [...]}).'
        )
    try:
        splits = json.loads(raw)
        assert isinstance(splits, list) and all(set(s) >= {"train", "val"} for s in splits)
    except (ValueError, AssertionError):
        raise StepError(f'{key} is not a valid splits file: expected a list of {{"train": [...], "val": [...]}}.')
    known = {p.name[: -len(".b2nd")] for p in pre_dir.rglob("*.b2nd") if not p.name.endswith("_seg.b2nd")}
    unknown = sorted({c for s in splits for c in s["train"] + s["val"]} - known)
    if unknown:
        raise StepError(f"{key} names cases that are not in {dataset}: {', '.join(unknown[:20])}")
    if fold != "all" and int(fold) >= len(splits):
        raise StepError(f"{key} defines {len(splits)} folds, fold {fold} was requested.")
    (pre_dir / "splits_final.json").write_bytes(raw)
    return {"splits": name, "splits_sha256": sha256_file(pre_dir / "splits_final.json")}


class Publisher(threading.Thread):
    """Publishes checkpoints whenever nnU-Net writes new ones, and logs every few minutes."""

    def __init__(self, ctx, prefix, fold_dir: Path, fold: str):
        super().__init__(daemon=True)
        self.ctx, self.prefix, self.fold_dir, self.fold = ctx, prefix, fold_dir, fold
        self.stop = threading.Event()
        self.seen = {}

    def snapshot(self, names) -> Path:
        # nnU-Net replaces checkpoints atomically (write tmp + rename); a hard link pins the current version
        snap = self.fold_dir.parent / f".snapshot-{uuid.uuid4().hex[:8]}" / self.fold_dir.name
        snap.mkdir(parents=True)
        for n in names:
            os.link(self.fold_dir / n, snap / n)
        return snap

    def publish(self, unit, names):
        names = [n for n in names if (self.fold_dir / n).is_file()]
        if not names:
            return
        snap = self.snapshot(names)
        try:
            self.ctx.store.publish(
                snap.parent, self.prefix, [f"{self.fold_dir.name}/{n}" for n in names], unit=unit, overwrite=True
            )
        finally:
            shutil.rmtree(snap.parent, ignore_errors=True)

    def logs(self):
        return [p.name for p in self.fold_dir.glob("*") if p.suffix in (".txt", ".png") or p.name == "debug.json"]

    def run(self):
        last_log = 0.0
        while not self.stop.wait(30):
            try:
                state = {n: (self.fold_dir / n).stat().st_mtime for n in CHECKPOINTS if (self.fold_dir / n).is_file()}
                if state and state != self.seen:
                    self.publish(layout.progress_unit(self.fold), list(state) + self.logs())
                    self.seen = state
                    last_log = time.time()
                elif time.time() - last_log > LOG_INTERVAL_S:
                    self.publish(f"log.fold_{self.fold}", self.logs())
                    last_log = time.time()
            except Exception as e:  # keep training even if S3 hiccups
                logger.warning("could not publish training progress: %s", e)


def run(ctx: Context):
    dataset, plans_name, configuration = parse_selection(ctx.selection())
    fold = os.environ.get("NNUNET_FOLD") or str(ctx.get("fold", "0"))
    trainer = ctx.get("trainer") or "nnUNetTrainer"
    dataset_id, _ = layout.parse_dataset_name(dataset)
    ctx.prepare()
    store = ctx.store

    pre_prefix = layout.preprocessed_prefix(dataset)
    pre_dir = layout.pod_dir("preprocessed") / dataset
    try:
        plans_marker = store.fetch(pre_prefix, pre_dir, unit=layout.plans_unit(plans_name))
        store.fetch(pre_prefix, pre_dir, unit="fingerprint")
        data_identifier = plans_marker["meta"]["configurations"][configuration]
        store.fetch(pre_prefix, pre_dir, unit=layout.data_unit(data_identifier))
    except (NotPublished, KeyError) as e:
        raise StepError(f"{dataset} / {plans_name} / {configuration} is not completely preprocessed: {e}")
    # what prediction needs to rebuild the inputs (channel rules, labels)
    raw_dir = layout.pod_dir("raw") / dataset
    store.fetch(layout.raw_prefix(dataset), raw_dir, include=lambda p: p == "kaapana.json")
    split_info = apply_custom_splits(ctx, dataset, pre_dir, fold)

    plans = json.loads((pre_dir / f"{plans_name}.json").read_text())
    # finetuning from an nnssl checkpoint (nnFoundation): nnUNetv2_train_pretrained, see pretrained.py
    finetune = pretrained.is_pretrained(plans)
    from_scratch = finetune and ctx.flag("from_scratch")
    if finetune:
        if trainer == "nnUNetTrainer":
            trainer = pretrained.default_trainer(plans_name, plans)
            print(f"Pretrained plans: using {trainer} (nnU-Net's recommendation for these plans).", flush=True)
        if not from_scratch:
            try:
                pretrained.fetch_for_plans(store, plans)
            except pretrained.PretrainedError as e:
                raise StepError(str(e))
    # nnU-Net names the results of a from-scratch baseline after <plans>__from_scratch
    results_plans = plans_name + ("__from_scratch" if from_scratch else "")
    model_prefix = layout.results_prefix(dataset, trainer, results_plans, configuration)
    model_dir = layout.pod_dir("results") / dataset / layout.model_folder_name(trainer, results_plans, configuration)
    fold_dir = model_dir / f"fold_{fold}"

    previous = plans["configurations"][configuration].get("previous_stage")
    if previous:
        prev_prefix = layout.results_prefix(dataset, trainer, plans_name, previous)
        try:
            store.fetch(
                prev_prefix,
                layout.pod_dir("results") / dataset / layout.model_folder_name(trainer, plans_name, previous),
                unit=layout.fold_unit(fold),
            )
        except NotPublished:
            raise StepError(f"{configuration} is a cascade stage: train {previous} fold {fold} first (same trainer).")

    continue_training = ctx.flag("continue_training")
    validation_only = ctx.flag("validation_only")
    if continue_training or validation_only:
        for unit in (layout.fold_unit(fold), layout.progress_unit(fold)):
            if store.is_published(model_prefix, unit):
                store.fetch(model_prefix, model_dir, unit=unit)
                print(f"Continuing from {unit}", flush=True)
                break
        else:
            raise StepError(f"Nothing to continue: no checkpoint of fold {fold} in {model_prefix}.")
    elif store.is_published(model_prefix, layout.fold_unit(fold)) and not ctx.flag("overwrite_existing"):
        raise StepError(
            f"Fold {fold} of {model_prefix} is already trained. Enable 'Continue training', "
            "'Validation only' or 'Overwrite existing fold'."
        )

    command = "nnUNetv2_train_pretrained" if finetune else "nnUNetv2_train"
    args = [command, str(dataset_id), configuration, fold, "-tr", trainer, "-p", plans_name]
    if from_scratch:
        args.append("--from_scratch")
    for key, flag in (
        ("npz", "--npz"),
        ("val_best", "--val_best"),
        ("disable_checkpointing", "--disable_checkpointing"),
    ):
        if ctx.flag(key):
            args.append(flag)
    if continue_training:
        args.append("--c")
    if validation_only:
        args.append("--val")
    if os.environ.get("NNUNET_DEVICE"):  # tests run on CPU; in Kaapana this is always cuda
        args += ["-device", os.environ["NNUNET_DEVICE"]]
    weights = ctx.get("pretrained_weights")
    if weights:
        if finetune:
            raise StepError("-pretrained_weights cannot be combined with pretrained (nnFoundation) plans.")
        args += ["-pretrained_weights", _fetch_checkpoint(ctx, weights)]

    fold_dir.mkdir(parents=True, exist_ok=True)
    publisher = Publisher(ctx, model_prefix, fold_dir, fold)
    publisher.start()
    try:
        run_nnunet(
            args, env={"nnUNet_n_proc_DA": str(ctx.advanced("n_proc_da") or os.environ.get("nnUNet_n_proc_DA", 12))}
        )
    finally:
        publisher.stop.set()
        publisher.join()

    files = [f"fold_{fold}"] + [
        n for n in ("dataset.json", "plans.json", "dataset_fingerprint.json") if (model_dir / n).is_file()
    ]
    if (raw_dir / "kaapana.json").is_file():  # missing for raw datasets uploaded by hand
        shutil.copy(raw_dir / "kaapana.json", model_dir / "kaapana.json")
        files.append("kaapana.json")
    store.publish(
        model_dir,
        model_prefix,
        files,
        unit=layout.fold_unit(fold),
        meta=provenance(
            ctx,
            dataset=dataset,
            trainer=trainer,
            plans=plans_name,
            configuration=configuration,
            fold=fold,
            pretrained=(plans.get("pretrain_info") or {}).get("checkpoint_name")
            if finetune and not from_scratch
            else None,
            **split_info,
        ),
        overwrite=True,
    )
    for unit in (layout.progress_unit(fold), f"log.fold_{fold}"):
        if store.is_published(model_prefix, unit):
            store.delete(model_prefix, unit)
    print(f"Published s3://{ctx.bucket}/nnunet/{model_prefix}/fold_{fold}/", flush=True)
    sync_dropdowns(ctx)


def _fetch_checkpoint(ctx: Context, s3_path: str) -> str:
    """-pretrained_weights from the project bucket, e.g. results/Dataset001_X/<model>/fold_0/checkpoint_final.safetensors"""
    rel = s3_path.strip().lstrip("/")
    rel = rel[len("nnunet/") :] if rel.startswith("nnunet/") else rel
    local = ctx.scratch / "pretrained_weights" / Path(rel).name
    local.parent.mkdir(parents=True, exist_ok=True)
    try:
        ctx.store._client().fget_object(ctx.store.bucket, ctx.store.key(rel), str(local))
    except S3Error:
        raise StepError(f"Pretrained weights s3://{ctx.store.bucket}/nnunet/{rel} not found.")
    return str(local)


if __name__ == "__main__":
    main(run)
