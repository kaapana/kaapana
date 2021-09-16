import os
import glob
from datetime import timedelta, date
import pydicom

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class DcmQueryOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 ae_title='NONE',
                 local_ae_title="KAAPANAQR",
                 pacs_host='ctp-dicom-service.flow.svc',
                 pacs_port='11112',
                 start_date: date=None,
                 end_date: date=None,
                 max_query_size: str = None,
                 env_vars=None,
                 level='study',
                 enable_proxy = False,
                 host_network = False,
                 execution_timeout=timedelta(minutes=20),
                 *args, **kwargs
                 ):

        if level not in ['study', 'series']:
            raise NameError('level must be either "study" or "series". \
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
            image=f"{default_registry}/dcmqr:0.1.1",
            name="dcmqr",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            host_network=host_network,
            enable_proxy=enable_proxy,
            execution_timeout=execution_timeout,
            *args, **kwargs
        )
