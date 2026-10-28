"""Form dropdowns from S3: rebuilds the backend's installed_models rows of the three nnU-Net kinds.

S3 stays the source of truth; every step calls sync() when it finishes. task_ids is what a workflow receives
as its selection (see the DAG forms).
"""

import json
import logging
import os
from collections import defaultdict

import requests

from kaapana_nnunet.gpu import gpu_memory_gb

logger = logging.getLogger(__name__)

KIND_RAW = "nnunetv2-raw"
KIND_PREPROCESSED = "nnunetv2-preprocessed"
KIND_MODEL = "nnunetv2-model"


def entries(store) -> dict[str, dict[str, dict]]:
    """{kind: {friendly_name: installed_models row}}"""
    out = {KIND_RAW: {}, KIND_PREPROCESSED: {}, KIND_MODEL: {}}

    for m in store.list_markers("raw"):
        dataset = m["prefix"].split("/", 1)[1]
        meta = m["marker"]["meta"]
        out[KIND_RAW][dataset] = {
            "task_ids": dataset,
            "description": f"{meta.get('cases', '?')} cases",
            "info": m["marker"]["created"][:16].replace("T", " "),
        }

    by_dataset = defaultdict(dict)
    for m in store.list_markers("preprocessed"):
        by_dataset[m["prefix"].split("/", 1)[1]][m["unit"]] = m["marker"]
    for dataset, units in by_dataset.items():
        for unit, marker in units.items():
            if not unit or not unit.startswith("plans."):
                continue
            plans = unit[len("plans.") :]
            gpu_gb = marker["meta"].get("gpu_memory_gb") or _gpu_memory_gb(store, dataset, plans)
            for configuration, data_identifier in marker["meta"].get("configurations", {}).items():
                data = units.get(f"data.{data_identifier}")
                if data is None:
                    continue
                name = f"{dataset} | {plans} | {configuration}"
                out[KIND_PREPROCESSED][name] = {
                    "task_ids": f"{dataset}|{plans}|{configuration}",
                    "model_plan": plans,
                    "models_name": configuration,
                    "description": f"{dataset}",
                    "info": data["created"][:16].replace("T", " "),
                    "form_defaults": {"gpu_memory_gb": gpu_gb},
                }

    folds = defaultdict(dict)
    for m in store.list_markers("results"):
        if m["unit"] and m["unit"].startswith("fold_"):
            folds[m["prefix"]][m["unit"][len("fold_") :]] = m["marker"]
    for prefix, by_fold in folds.items():
        _, dataset, model = prefix.split("/", 2)
        trainer, plans, configuration = model.split("__")
        name = f"{dataset} | {configuration} | {trainer} | {plans}"
        out[KIND_MODEL][name] = {
            "task_ids": prefix,
            "model_network_trainer": trainer,
            "model_plan": plans,
            "models_name": configuration,
            "description": dataset,
            "info": "folds " + ", ".join(sorted(by_fold)),
        }
    return out


def _gpu_memory_gb(store, dataset: str, plans: str) -> int:
    """For plans published before the requirement was recorded in their marker."""
    try:
        return gpu_memory_gb(store.read_json(f"preprocessed/{dataset}", f"{plans}.json"))
    except Exception as e:
        logger.warning("GPU memory of %s/%s unknown, using the default: %s", dataset, plans, e)
        return gpu_memory_gb({"configurations": {}})


def sync(ctx):
    from kaapana_client.settings import ServicesSettings

    url = f"{os.environ.get('KAAPANA_BACKEND_URL') or ServicesSettings().kaapana_backend_url}/client/installed_models/sync"
    headers = {"Project": json.dumps(ctx.project)}
    for kind, rows in entries(ctx.store).items():
        res = requests.put(url, json={"installed_models": rows, "kind": kind}, headers=headers, timeout=30)
        if res.status_code != 200:
            raise RuntimeError(f"[{res.status_code}] {res.text}")
        logger.info("dropdown %s: %d entries", kind, len(rows))
