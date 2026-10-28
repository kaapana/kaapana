"""Pretrained nnssl checkpoints (nnFoundation) for finetuning with nnU-Net.

nnFoundationCNN and nnFoundationViT ship with the image ($NNUNET_BUNDLED_PRETRAINED, see the Dockerfile), so no
internet access is needed. Other nnssl checkpoints can be uploaded to nnunet/pretrained/<name>/
(adaptation_plan.json, checkpoint_final.pth) and registered with nnunetv2-refresh.

Either way the checkpoint appears at /nnunet/pretrained/<folder>/ in every pod. nnU-Net writes that absolute
checkpoint path into the adapted plans, which is why all pods use the same /nnunet root (see layout).
"""

import json
import os
from pathlib import Path

from kaapana_nnunet import layout
from kaapana_nnunet.store import NotPublished

# Hugging Face repositories (CC-BY-SA-4.0); the folder name is what nnU-Net's own downloader uses
KNOWN = {
    "nnFoundationCNN": "MIC-DKFZ/nnFoundationCNN",
    "nnFoundationViT": "MIC-DKFZ/nnFoundationViT",
}
REQUIRED_FILES = ("adaptation_plan.json", "checkpoint_final.pth")


class PretrainedError(Exception):
    pass


def folder_name(name: str) -> str:
    return KNOWN.get(name, name).replace("/", "_")


def prefix(name: str) -> str:
    return f"pretrained/{folder_name(name)}"


def bundled(name: str) -> Path | None:
    root = os.environ.get("NNUNET_BUNDLED_PRETRAINED")
    folder = Path(root) / folder_name(name) if root else None
    return folder if folder and all((folder / f).is_file() for f in REQUIRED_FILES) else None


def fetch(store, name: str) -> Path:
    """Provide the checkpoint at /nnunet/pretrained/<folder>/ and return the checkpoint path."""
    local = layout.pod_dir("pretrained") / folder_name(name)
    source = bundled(name)
    if source:
        if not local.exists():
            local.symlink_to(source, target_is_directory=True)
        return local / "checkpoint_final.pth"
    try:
        store.fetch(prefix(name), local)
    except NotPublished:
        raise PretrainedError(
            f"The pretrained model '{name}' is neither bundled ({', '.join(KNOWN)}) nor in this project "
            f"(nnunet/{prefix(name)}/). Upload the folder (adaptation_plan.json, checkpoint_final.pth) "
            "and run nnunetv2-refresh."
        )
    return local / "checkpoint_final.pth"


def uploaded(store) -> list[str]:
    """Folders under nnunet/pretrained/ that were uploaded by hand and are not registered yet."""
    names = set()
    for obj in store._client().list_objects(store.bucket, prefix=store.key("pretrained") + "/", recursive=True):
        rel = obj.object_name[len(store.key("pretrained")) + 1 :]
        if "/" in rel:
            names.add(rel.split("/", 1)[0])
    return sorted(n for n in names if not store.is_published(f"pretrained/{n}"))


def fetch_for_plans(store, plans: dict):
    """Fetch the checkpoint an adapted plans file points to (no-op for normal plans)."""
    path = (plans.get("pretrain_info") or {}).get("checkpoint_path")
    if not path:
        return
    folder = Path(path).parent
    if folder.parent != layout.pod_dir("pretrained"):
        raise PretrainedError(f"The plans point to {path}, which is not a Kaapana pretrained model folder.")
    fetch(store, folder.name)


def default_trainer(plans_name: str, plans: dict) -> str:
    """The trainer nnU-Net's documentation pairs with these plans (finetuning_from_nnssl_checkpoints.md)."""
    if plans_name.startswith("ptPlans_dynamic__"):
        return "DynamicPretrainedTrainer"
    architecture = json.dumps(plans.get("configurations", {}).get("3d_fullres", {}).get("architecture", {}))
    return "PretrainedTrainer_Primusx" if "Primus" in architecture else "PretrainedTrainer"


def is_pretrained(plans: dict) -> bool:
    return "pretrain_info" in plans
