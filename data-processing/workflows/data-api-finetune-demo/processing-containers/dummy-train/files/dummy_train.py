"""Dummy fine-tune task.

This is a *demo* task: it does no training. Its job is to prove the query-input
channels were frozen, downloaded by the upstream ``data-api-download`` tasks, and
handed over on disk via IOMapping — and to emit a "model" the downstream
``data-api-upload`` task can write back to the Data API.

The ``segmentations`` channel (DICOM-SEG) is required. The ``model`` channel
(base model, ``has_key model``) is OPTIONAL: an empty/absent model channel
means "train the first model from scratch" (the bootstrap run). The task writes
a tiny dummy model + a ``training_manifest.json`` (legible artefact), plus an
``upload_manifest.json`` that tells the upload task what entity to create:
the metadata to attach (``model``) and the upstream entity IDs (lineage).
Provenance is NOT written here — the upload operator stamps it from trusted
run-context env so a producer can't forge it.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("data-api-finetune-train")

UPLOAD_MANIFEST_NAME = "upload_manifest.json"


def _inspect_channel(name: str, path: Path, *, allow_empty: bool = False) -> List[dict]:
    """List the per-entity subdirectories arriving on one input channel.

    With ``allow_empty`` a missing/empty mount returns ``[]`` instead of raising
    — used for the optional base-model channel (train-from-scratch bootstrap).
    """
    if not path.is_dir():
        if allow_empty:
            logger.info(
                "Channel '%s' has no mount at %s — treating as empty.", name, path
            )
            return []
        raise RuntimeError(f"Input channel '{name}' has no mount at {path}")

    entities = sorted(p for p in path.iterdir() if p.is_dir())
    if not entities:
        if allow_empty:
            logger.info("Channel '%s' is empty — training from scratch.", name)
            return []
        raise RuntimeError(f"Input channel '{name}' is empty at {path}")

    summary = []
    for entity_dir in entities:
        files = sorted(
            str(f.relative_to(entity_dir)) for f in entity_dir.rglob("*") if f.is_file()
        )
        logger.info("[%s] %s -> %d file(s)", name, entity_dir.name, len(files))
        summary.append({"entity_id": entity_dir.name, "files": files})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--segmentations", type=Path, default=Path("/home/kaapana/segmentations")
    )
    parser.add_argument("--model", type=Path, default=Path("/home/kaapana/model"))
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("/home/kaapana/output")
    )
    args = parser.parse_args()

    segmentations = _inspect_channel("segmentations", args.segmentations)
    # Optional: no base model -> train the first model from scratch.
    base_model = _inspect_channel("model", args.model, allow_empty=True)
    from_scratch = not base_model

    args.output.mkdir(parents=True, exist_ok=True)

    base_model_ids = [m["entity_id"] for m in base_model]
    upstream_entity_ids = [s["entity_id"] for s in segmentations] + base_model_ids

    manifest = {
        "trained": False,
        "note": "demo task — no real training performed",
        "from_scratch": from_scratch,
        "segmentations": segmentations,
        "base_model": base_model,
    }
    (args.output / "training_manifest.json").write_text(json.dumps(manifest, indent=2))
    (args.output / "model.dummy").write_text(
        "Dummy fine-tuned model produced from "
        f"{len(segmentations)} segmentation entity/-ies and "
        f"{len(base_model)} base-model entity/-ies"
        f"{' (trained from scratch)' if from_scratch else ''}.\n"
    )

    # Instructions for the downstream data-api-upload task: create a new entity
    # carrying a model, with lineage to its inputs. Provenance is added by
    # the upload operator from trusted run-context env, NOT from here.
    # ``finetune-note`` is this workflow's own key (registered by the
    # ensure_schema task); attaching it here exercises that key end-to-end.
    upload_manifest = {
        "store": "s3",
        "metadata": {
            "model": {
                "name": "dummy-finetuned-model",
                "framework": "dummy",
                "trained_from_scratch": from_scratch,
                "base_model_entity_ids": base_model_ids,
            },
            "finetune-note": {
                "note": "fine-tuned in the data-api demo",
                "reviewed": False,
            },
        },
        "upstream_entity_ids": upstream_entity_ids,
    }
    (args.output / UPLOAD_MANIFEST_NAME).write_text(
        json.dumps(upload_manifest, indent=2)
    )

    logger.info(
        "Dummy fine-tune done: %d segmentation + %d model entities (from_scratch=%s) -> %s",
        len(segmentations),
        len(base_model),
        from_scratch,
        args.output,
    )


if __name__ == "__main__":
    main()
