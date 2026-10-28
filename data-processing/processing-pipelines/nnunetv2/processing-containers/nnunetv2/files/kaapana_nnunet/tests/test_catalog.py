"""Dropdown entries are built from complete units only."""

import json

from kaapana_nnunet import catalog, layout
from kaapana_nnunet.gpu import gpu_memory_gb

from tests.test_store import make_tree, pytestmark  # noqa: F401


def test_entries(store, tmp_path):
    ds = "Dataset001_Liver"
    make_tree(
        tmp_path / "p",
        {
            "dataset.json": b"{}",
            "dataset_fingerprint.json": b"{}",
            "nnUNetPlans.json": json.dumps({"configurations": {}}).encode(),
            "nnUNetPlans_3d_fullres/c.b2nd": b"x",
            "nnUNetPlans_2d/c.b2nd": b"y",
        },
    )
    make_tree(tmp_path / "r", {"dataset.json": b"{}"})
    store.publish(tmp_path / "r", layout.raw_prefix(ds), meta={"cases": 3})
    pre = layout.preprocessed_prefix(ds)
    configs = {"2d": "nnUNetPlans_2d", "3d_fullres": "nnUNetPlans_3d_fullres", "3d_lowres": "nnUNetPlans_3d_lowres"}
    store.publish(tmp_path / "p", pre, ["nnUNetPlans.json"], unit="plans.nnUNetPlans", meta={"configurations": configs})
    store.publish(tmp_path / "p", pre, ["nnUNetPlans_3d_fullres"], unit="data.nnUNetPlans_3d_fullres")
    make_tree(
        tmp_path / "m", {"fold_0/checkpoint_final.safetensors": b"w", "fold_2/checkpoint_final.safetensors": b"w"}
    )
    model = layout.results_prefix(ds, "nnUNetTrainer", "nnUNetPlans", "3d_fullres")
    store.publish(tmp_path / "m", model, ["fold_0"], unit="fold_0")
    store.publish(tmp_path / "m", model, ["fold_2"], unit="progress.fold_2")  # unfinished: not a fold

    got = catalog.entries(store)
    assert got[catalog.KIND_RAW] == {
        ds: {"task_ids": ds, "description": "3 cases", "info": got[catalog.KIND_RAW][ds]["info"]}
    }
    assert [e["task_ids"] for e in got[catalog.KIND_PREPROCESSED].values()] == [f"{ds}|nnUNetPlans|3d_fullres"]
    # plans published without the requirement in their marker: read from the plans file
    assert [e["form_defaults"] for e in got[catalog.KIND_PREPROCESSED].values()] == [{"gpu_memory_gb": 11}]
    (entry,) = got[catalog.KIND_MODEL].values()
    assert entry["task_ids"] == model and entry["info"] == "folds 0"


def test_gpu_memory():
    def plans(planner="ExperimentPlanner", network="ResidualEncoderUNet"):
        arch = {"network_class_name": network}
        return {"experiment_planner_used": planner, "configurations": {"3d_fullres": {"architecture": arch}}}

    assert gpu_memory_gb(plans()) == 11
    assert gpu_memory_gb(plans("nnUNetPlannerResEncM")) == 11
    assert gpu_memory_gb(plans("nnUNetPlannerResEncL")) == 18
    assert gpu_memory_gb(plans("nnUNetPlannerResEncXL")) == 32
    assert gpu_memory_gb(plans(network="ResEncL")) == 18  # nnFoundationCNN plans keep the base planner's name
    assert gpu_memory_gb(plans(network="PrimusM")) == 32
    assert gpu_memory_gb(plans(), gpu_memory_target="20") == 20
