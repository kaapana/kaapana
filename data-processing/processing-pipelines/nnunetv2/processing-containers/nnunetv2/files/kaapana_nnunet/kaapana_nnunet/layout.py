"""Where nnU-Net folders live: in the project bucket and inside a pod.

S3 (project bucket, see store.S3Store for the marker semantics)::

    nnunet/raw/<Dataset>/                          unit: default (_DONE.json)
    nnunet/preprocessed/<Dataset>/                 units: fingerprint, plans.<plans>, data.<data_identifier>
    nnunet/results/<Dataset>/<tr>__<plans>__<cfg>/ units: fold_<f>, progress.fold_<f>
    nnunet/pretrained/<name>/                      unit: default
    nnunet/code/<name>/                            unit: default

Inside a pod every nnU-Net folder sits at the same absolute path (/nnunet/...), because nnU-Net writes
absolute paths into some files (e.g. the checkpoint path of nnFoundation plans). /nnunet/<x> are symlinks
into the run's scratch directory on the workflow volume.
"""

import os
import re
from pathlib import Path

FOLDERS = ("raw", "preprocessed", "results", "pretrained")

DATASET_RE = re.compile(r"^Dataset(\d{3})_([A-Za-z0-9_-]+)$")


def pod_root() -> Path:
    return Path(os.environ.get("NNUNET_POD_ROOT", "/nnunet"))


def pod_dir(name: str) -> Path:
    return pod_root() / name


def prepare_pod_dirs(scratch: Path) -> dict:
    """Point /nnunet/<folder> into ``scratch`` and export the nnU-Net environment variables."""
    pod_root().mkdir(parents=True, exist_ok=True)
    for name in FOLDERS:
        target = scratch / name
        target.mkdir(parents=True, exist_ok=True)
        link = pod_root() / name
        if link.is_symlink() or link.exists():
            if link.is_symlink() and link.resolve() == target.resolve():
                continue
            if link.is_symlink():
                link.unlink()
            else:
                raise RuntimeError(f"{link} exists and is not a symlink")
        link.symlink_to(target, target_is_directory=True)
    env = {
        "nnUNet_raw": str(pod_dir("raw")),
        "nnUNet_preprocessed": str(pod_dir("preprocessed")),
        "nnUNet_results": str(pod_dir("results")),
        "nnssl_pretrained_models": str(pod_dir("pretrained")),
    }
    os.environ.update(env)
    return env


def dataset_name(dataset_id: int, name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_")
    if not clean:
        raise ValueError("the dataset name must contain letters or digits")
    if not 1 <= dataset_id <= 999:
        raise ValueError(f"nnU-Net dataset IDs are 1-999, got {dataset_id}")
    return f"Dataset{dataset_id:03d}_{clean}"


def parse_dataset_name(name: str) -> tuple[int, str]:
    m = DATASET_RE.match(name)
    if not m:
        raise ValueError(f"{name!r} is not an nnU-Net dataset name (DatasetXXX_Name)")
    return int(m.group(1)), m.group(2)


def raw_prefix(dataset: str) -> str:
    return f"raw/{dataset}"


def preprocessed_prefix(dataset: str) -> str:
    return f"preprocessed/{dataset}"


def model_folder_name(trainer: str, plans: str, configuration: str) -> str:
    return f"{trainer}__{plans}__{configuration}"


def results_prefix(dataset: str, trainer: str, plans: str, configuration: str) -> str:
    return f"results/{dataset}/{model_folder_name(trainer, plans, configuration)}"


def fold_unit(fold: str) -> str:
    return f"fold_{fold}"


def progress_unit(fold: str) -> str:
    return f"progress.fold_{fold}"


def plans_unit(plans: str) -> str:
    return f"plans.{plans}"


def data_unit(data_identifier: str) -> str:
    return f"data.{data_identifier}"


def used_dataset_ids(store) -> set[int]:
    """IDs taken in the project, complete or not (a half-written upload still blocks its ID)."""
    ids = set()
    for top in ("raw", "preprocessed", "results"):
        for obj in store._client().list_objects(store.bucket, prefix=store.key(top) + "/"):
            name = obj.object_name.rstrip("/").rsplit("/", 1)[-1]
            m = DATASET_RE.match(name)
            if m:
                ids.add(int(m.group(1)))
    return ids


def next_free_dataset_id(store, start: int = 1) -> int:
    used = used_dataset_ids(store)
    for i in range(start, 1000):
        if i not in used:
            return i
    raise RuntimeError("all nnU-Net dataset IDs (1-999) are in use in this project")


RESERVATION = ".reserved"


def _names_with_id(store, dataset_id: int) -> set[str]:
    names = set()
    for top in ("raw", "preprocessed", "results"):
        for obj in store._client().list_objects(store.bucket, prefix=store.key(top) + f"/Dataset{dataset_id:03d}_"):
            names.add(obj.object_name.rstrip("/").rsplit("/", 1)[-1])
    return names


def reserve_dataset(store, title: str, dataset_id: int = 0) -> str:
    """Claim an nnU-Net dataset ID for a new raw dataset by writing a reservation object.
    Two runs that race for the same ID see each other's reservation; the older reservation (ties: the
    smaller name) keeps the ID, the other run moves on to the next ID. Returns the dataset name."""
    from io import BytesIO

    from minio.error import S3Error

    def claim_order(n):
        # existing data without a reservation object is older than any reservation
        try:
            stat = store._client().stat_object(store.bucket, store.key(raw_prefix(n), RESERVATION))
            return (1, stat.last_modified, n)
        except S3Error:
            return (0, None, n)

    fixed = bool(dataset_id)
    candidate = dataset_id or next_free_dataset_id(store)
    while True:
        name = dataset_name(candidate, title)
        others = _names_with_id(store, candidate) - {name}
        if not others:
            key = store.key(raw_prefix(name), RESERVATION)
            store._client().put_object(store.bucket, key, BytesIO(b""), 0)
            others = _names_with_id(store, candidate) - {name}
            if not others:
                return name
            mine = claim_order(name)
            theirs = [claim_order(n) for n in others]
            if all(t[0] == 1 and (t[1], t[2]) > (mine[1], mine[2]) for t in theirs):
                return name
            store._client().remove_object(store.bucket, key)
        if fixed:
            raise ValueError(f"dataset ID {candidate} is already used in this project by {', '.join(sorted(others))}")
        candidate = next_free_dataset_id(store, candidate + 1)


def release_dataset(store, name: str):
    store._client().remove_object(store.bucket, store.key(raw_prefix(name), RESERVATION))
