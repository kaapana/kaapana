from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class TotalSegmentatorOperator(KaapanaBaseOperator):
    """
    Executes the total segmentator algorithm on a given 3D CT nifti image.
    The algorithm segments 104 body structures and stores them in single file nifti format.

    Expects the pretrained weights already to be downloaded (use LocalGetTotalSegmentatorModels for that).
    A Nvidia GPU is required to run the algorithm.

    - Publication:
      Wasserthal, J., Meyer, M., Breit, H. C., Cyriac, J., Yang, S., & Segeroth, M. (2022).
      TotalSegmentator: robust segmentation of 104 anatomical structures in CT images.
      arXiv preprint arXiv:2208.05868.

    - Code: https://github.com/wasserth/TotalSegmentator

    :param task: Task to execute. Currently, on 'total' is supported.
    :type task: str
    """

    execution_timeout = timedelta(minutes=120)

    def __init__(
        self,
        dag,
        task,
        name="total-segmentator",
        output_type="nifti",
        multilabel=False,
        fast=False,
        preview=False,
        statistics=True,
        radiomics=True,
        body_seg=False,
        force_split=False,
        quiet=False,
        verbose=False,
        roi_subset=None,
        nr_thr_resamp=1,
        nr_thr_saving=6,
        env_vars=None,
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        if env_vars is None:
            env_vars = {}

        # Tasks available:
        # total
        # lung_vessels
        # cerebral_bleed
        # hip_implant
        # coronary_arteries
        # body
        # pleural_pericard_effusion
        # liver_vessels
        # bones_extremities
        # tissue_types
        # heartchambers_highres
        # head
        # aortic_branches
        # heartchambers_test
        # bones_tissue_test
        # aortic_branches_test
        # test

        envs = {
            "TASK": str(task),
            "OUTPUT_TYPE": str(output_type),
            "MULTILABEL": str(multilabel),
            "FAST": str(fast),
            "PREVIEW": str(preview),
            "STATISTICS": str(statistics),
            "RADIOMICS": str(radiomics),
            "BODYSEG": str(body_seg),
            "FORCESPLIT": str(force_split),
            "QUIET": str(quiet),
            "VERBOSE": str(verbose),
            "ROI_SUBSET": "None" if not roi_subset else " ".join(roi_subset),
            "NR_THR_RESAMP": str(nr_thr_resamp),
            "NR_THR_SAVING": str(nr_thr_saving),
        }
        if task == "combine-masks":
            ram_mem_mb = 5000
            gpu_mem_mb = None
        else:
            ram_mem_mb = 13000
            gpu_mem_mb = 11900

        env_vars.update(envs)
        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/total-segmentator:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            keep_parallel_id=False,
            enable_proxy=True,
            env_vars=env_vars,
            ram_mem_mb=ram_mem_mb,
            gpu_mem_mb=gpu_mem_mb,
            **kwargs,
        )
