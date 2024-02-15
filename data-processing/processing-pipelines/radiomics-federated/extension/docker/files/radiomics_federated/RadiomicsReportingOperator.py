import os
import glob
from datetime import timedelta
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
    SERVICES_NAMESPACE,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class RadiomicsReportingOperator(KaapanaBaseOperator):
    def __init__(
        self,
        dag,
        name="radiomics-reporting-operator",
        execution_timeout=timedelta(minutes=20),
        minio_path="analysis-scripts/FedRad-Analysis.ipynb",
        *args,
        **kwargs,
    ):
        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/radiomics-federated-analysis:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            cmds=["/bin/bash"],
            arguments=[
                f"/files/run_notebook.sh",
            ],
            execution_timeout=execution_timeout,
            ram_mem_mb=1000,
            ram_mem_mb_lmt=3000,
            env_vars={
                "MINIO_PATH": minio_path,
                "MINIO_SERVICE": f"minio-service.{SERVICES_NAMESPACE}.svc:9000",
                "MINIO_USER": "kaapanaminio",
                "MINIO_PASSWORD": "Kaapana2020",
            }
            * args,
            **kwargs,
        )
