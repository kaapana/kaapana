import os
import glob
from datetime import timedelta
import pydicom

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class TemplateOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 aetitle=None,
                 study_uid=None,
                 study_description=None,
                 patient_id=None,
                 patient_name=None,
                 env_vars=None,
                 execution_timeout=timedelta(minutes=10),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "AETITLE": str(aetitle),
            "STUDY_UID": str(study_uid),
            "STUDY_DES": str(study_description),
            "PAT_ID": str(patient_id),
            "PAT_NAME": str(patient_name),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image="{}{}/<REPLACE>:3.6.4-vdev".format(default_registry, default_project),
            name="REPLACE",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            *args, **kwargs
        )
