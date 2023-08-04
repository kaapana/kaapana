import os
import glob
from datetime import timedelta, date
import pydicom

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE


class DcmQueryOperator(KaapanaBaseOperator):
    def __init__(
        self,
        dag,
        ae_title="NONE",
        local_ae_title="KAAPANAQR",
        pacs_host=f"ctp-dicom-service.{SERVICES_NAMESPACE}.svc",
        pacs_port="11112",
        start_date: date = None,
        end_date: date = None,
        max_query_size: str = None,
        env_vars=None,
        level="study",
        execution_timeout=timedelta(minutes=20),
        **kwargs,
    ):
        if level not in ["study", "series"]:
            raise NameError(
                'level must be either "study" or "series". \
                If batch, an operator folder next to the batch folder with .dcm files is expected. \
                If element, *.dcm are expected in the corresponding operator with .dcm files is expected.'
            )

        if env_vars is None:
            env_vars = {}

        envs = {
            "PACS_HOST": str(pacs_host),
            "PACS_PORT": str(pacs_port),
            "LOCAL_AE_TITLE": str(local_ae_title),
            "AE_TITLE": str(ae_title),
            "LEVEL": str(level),
        }

        if start_date:
            env["START_DATE"] = start_date.strftime("%Y-%m-%d")

        if end_date:
            env["END_DATE"] = end_date.strftime("%Y-%m-%d")

        if max_query_size:
            env["MAX_QUERY_SIZE"] = int(max_query_size)

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/dcmqr:{KAAPANA_BUILD_VERSION}",
            name="dcmqr",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            **kwargs,
        )
