from datetime import timedelta
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class JupyterlabReportingOperator(KaapanaBaseOperator):
    """
    This operator executes the jupyter notebook at $/WORKFLOW_DIR/<notebook_filename> and converts the result into a report file in the <output_format>.

    This Operator is commonly used in between two LocalMinioOperators.
    The first LocalMinioOperator would download the jupyter notebook from a MinIO bucket into the WORKFLOW_DIR.
    The second LocalMinioOperator uploads the report into the staticwebsiteresults bucket.
    """

    def __init__(
        self,
        dag,
        notebook_filename: str,
        output_format: str = "html",
        name="jupyterlab-reporting-operator",
        execution_timeout=timedelta(minutes=20),
        *args,
        **kwargs,
    ):
        """
        :param: notebook_filename: File name of the jupyter notebook filename.
        :param: output_format: Comma separated list of output formats the jupyter notebook should be converted to after execution.
        """
        env_vars = {
            "NOTEBOOK_FILENAME": notebook_filename,
            "OUTPUT_FORMAT": output_format,
        }
        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/jupyterlab-reporting:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=1000,
            ram_mem_mb_lmt=3000,
            env_vars=env_vars,
            *args,
            **kwargs,
        )
