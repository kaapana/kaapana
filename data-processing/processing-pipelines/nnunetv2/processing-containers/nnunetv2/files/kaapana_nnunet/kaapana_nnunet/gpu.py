"""GPU memory of a training: recorded with the plans, shown as default in the Train form and reserved per fold."""


def gpu_memory_gb(plans: dict, gpu_memory_target=None) -> int:
    """GPU memory one training of these plans needs; nnunetv2-train reserves it per fold.

    nnU-Net sizes the presets for GPU classes (default and ResEnc M: >= 10 GB, L: 24 GB, XL: 40 GB). The
    values are what a training actually uses: ResEnc-L measured 18.6 GB on an RTX 3090 (nnFoundationCNN),
    XL and Primus are scaled estimates. 18 GB is above half of a 24 GB GPU, so two such folds never share one.
    """
    if gpu_memory_target:
        return int(round(float(gpu_memory_target)))
    planner = plans.get("experiment_planner_used", "")
    networks = " ".join(
        str((c.get("architecture") or {}).get("network_class_name", "")) for c in plans["configurations"].values()
    )
    if "Primus" in networks or planner.endswith("ResEncXL"):
        return 32
    if "ResEncL" in networks or planner.endswith("ResEncL"):
        return 18
    return 11
