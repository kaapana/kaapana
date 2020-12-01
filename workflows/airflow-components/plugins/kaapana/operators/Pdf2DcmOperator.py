import os
import glob
from datetime import timedelta
import pydicom

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class Pdf2DcmOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 dicom_operator,
                 pdf_title='KAAPANA PDF',
                 env_vars=None,
                 execution_timeout=timedelta(minutes=10),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "DICOM_IN_DIR": str(dicom_operator.operator_out_dir),
            "PDF_TITLE": str(pdf_title),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image="{}{}/pdf2dcm:3.6.4-vdev".format(default_registry, default_project),
            name="pdf2dcm",
            image_pull_secrets=["registry-secret"],
            image_pull_policy="Always",
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            *args, **kwargs
        )
