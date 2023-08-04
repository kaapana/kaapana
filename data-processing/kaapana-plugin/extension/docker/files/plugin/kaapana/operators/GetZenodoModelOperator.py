from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta
import os


class GetZenodoModelOperator(KaapanaBaseOperator):
    """
    Operator to download models from https://zenodo.org/ and extract them into the desired location on the file system.

    **Inputs:**

        * model_dir: Location where to extract the model archive
        * task_ids: List of comma separated tasks that should be downloaded

    **Outputs:**

        * The downloaded model is available for inference.
    """

    execution_timeout = timedelta(minutes=240)

    def __init__(
        self,
        dag,
        model_dir="/models/nnUNet",
        name="get-zenodo-models",
        task_ids=None,
        enable_proxy=True,
        delete_output_on_start=False,
        env_vars={},
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        """
        :param model_dir: The directory relative to SLOW_DATA_DIR/workflows where the downloaded models should be extracted. Defaults to "/models/nnUNet".
        :type model_dir: str
        :param name: The base name of the pod. Defaults to "get-zenodo-models".
        :type name: str
        :param task_ids: A comma separated list of the task IDs associated with the models that should be downloaded and extracted. Defaults to None.
        :type task_ids: str
        :param enable_proxy: Determines if the proxy should be enabled. Defaults to True.
        :type enable_proxy: bool
        :param delete_output_on_start: Determines if the operator output directory should be deleted on start. Defaults to False.
        :type delete_output_on_start: bool
        """

        envs = {"MODEL_DIR": str(model_dir), "LOG_LEVEL": "INFO"}
        env_vars.update(envs)

        if task_ids is not None:
            env_vars["TASK_IDS"] = task_ids

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/download-zenodo-models:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            enable_proxy=enable_proxy,
            delete_output_on_start=delete_output_on_start,
            ram_mem_mb=1000,
            **kwargs,
        )
