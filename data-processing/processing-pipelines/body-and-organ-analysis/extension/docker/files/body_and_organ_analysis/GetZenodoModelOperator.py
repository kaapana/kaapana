from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class GetZenodoModelOperator(KaapanaBaseOperator):
    """
    Operator to provide the model weights required by the body-and-organ-analysis workflow.

    The weights are extracted into the project's model volume from the archives packaged
    in the get-body-and-organ-analysis-models image. If an archive is not packaged in the
    image, it is downloaded from https://zenodo.org/ instead.

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
        model_dir="/models",
        name="get-boa-models",
        task_ids=None,
        enable_proxy=True,
        delete_output_on_start=False,
        env_vars={},
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        """
        :param model_dir: The directory where the downloaded models should be extracted.
        :type model_dir: str
        :param name: The base name of the pod. Defaults to "get-boa-models".
        :type name: str
        :param task_ids: A comma separated list of the task IDs associated with the models that should be downloaded and extracted. Defaults to None.
        :type task_ids: str
        :param enable_proxy: Determines if the proxy should be enabled. Defaults to True.
        :type enable_proxy: bool
        :param delete_output_on_start: Determines if the operator output directory should be deleted on start. Defaults to False.
        :type delete_output_on_start: bool
        """

        envs = {
            "MODEL_DIR": str(model_dir),
            "LOG_LEVEL": "INFO",
            "no_proxy": "localhost,.svc,.cluster",
        }
        env_vars.update(envs)

        if task_ids is not None:
            env_vars["TASK_IDS"] = task_ids

        if "labels" not in kwargs or not isinstance(kwargs["labels"], dict):
            kwargs["labels"] = {}

        kwargs["labels"]["network-access-external-ips"] = "true"

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/get-body-and-organ-analysis-models:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            enable_proxy=enable_proxy,
            delete_output_on_start=delete_output_on_start,
            ram_mem_mb=1000,
            **kwargs,
        )
