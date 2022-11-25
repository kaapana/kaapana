from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version


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

    :param task: Task you would like to execute. Currently, on 'total' is supported.
    :type task: str
    """

    execution_timeout = timedelta(minutes=10)

    def __init__(self,
                 dag,
                 name="total-segmentator",
                 task="total",
                 env_vars=None,
                 execution_timeout=execution_timeout,
                 **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "TASK": str(task),
        }

        env_vars.update(envs)
        super().__init__(
            dag=dag,
            image=f"{default_registry}/total-segmentator:{kaapana_build_version}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            keep_parallel_id=False,
            env_vars=env_vars,
            ram_mem_mb=12000,
            gpu_mem_mb=8000,
            **kwargs
        )
