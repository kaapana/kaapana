from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class DcmValidatorOperator(KaapanaBaseOperator):
    """
    Operator to validate Dicoms. Validation results will be stored as a HTML
    file in the provided Operator Output directory

    This operator currently implements two algorithm to validate dicoms.
    dciodvfy: https://dclunie.com/dicom3tools/dciodvfy.html
    dicom-validator: https://pypi.org/project/dicom-validator/
    """

    def __init__(
        self,
        dag,
        name="dicom-validator",
        execution_timeout=timedelta(minutes=15),
        validator_alg="dciodvfy",
        exit_on_error=False,
        env_vars=None,
        *args,
        **kwargs,
    ):
        """
        :param validator_alg: Defines which validation algorithm will be used. OneOf: dciodvfy, pydicomvalidator
        :param exit_on_error: Defines if the operator will raise an error on validation fail.
        """
        if env_vars is None:
            env_vars = {}

        envs = {
            "VALIDATOR_ALGORITHM": validator_alg,
            "EXIT_ON_ERROR": str(exit_on_error),
        }

        env_vars.update(envs)
        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/dicom-validator:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            ram_mem_mb=1000,  # Histopathology image from deletion-dataset was failing with OOM
            cpu_millicores=200,
            cpu_millicores_lmt=500,
            *args,
            **kwargs,
        )
