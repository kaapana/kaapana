from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class TotalSegmentatorV2Operator(KaapanaBaseOperator):
    """
    Executes the total segmentator algorithm on a given 3D CT or MR nifti image.
    The algorithm segments 117 (CT) and 50 (MR) body structures and stores them in single file nifti format.

    Expects the pretrained weights already to be downloaded (use LocalGetTotalSegmentatorModels for that).

    - Publication:
      Wasserthal, J., Meyer, M., Breit, H. C., Cyriac, J., Yang, S., & Segeroth, M. (2022).
      TotalSegmentator: robust segmentation of 104 anatomical structures in CT images.
      arXiv preprint arXiv:2208.05868.

    - Code: https://github.com/wasserth/TotalSegmentator

    :param task: Task to execute.
    :type task: str
    """

    def __init__(
        self,
        dag,
        task=None,
        name="total-segmentator-v2",
        output_type="nifti",
        multilabel=True,
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
        modality='CT',
        env_vars=None,
        execution_timeout=timedelta(minutes=120),
        **kwargs,
    ):
        if env_vars is None:
            env_vars = {}

        envs = {
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
            "TASK_MODALITY": str(modality)
        }
        if task:
            envs['TASK'] = str(task)
        ram_mem_mb = 16000
        gpu_mem_mb = 11900

        env_vars.update(envs)
        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/total-segmentator-v2:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            keep_parallel_id=False,
            enable_proxy=True,
            env_vars=env_vars,
            ram_mem_mb=ram_mem_mb,
            gpu_mem_mb=gpu_mem_mb,
            retries=3,
            **kwargs,
        )
