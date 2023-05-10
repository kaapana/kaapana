import os
import glob
from datetime import timedelta
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
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
            image=f"{DEFAULT_REGISTRY}/jupyterlab:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            cmds=["/bin/bash"],
            arguments=[
                "-c",
                f"jupyter nbconvert --to html --execute --no-input /minio/{minio_path}  --output-dir /minio/staticwebsiteresults/$DAG_ID --output $RUN_ID-report.html",
            ],
            execution_timeout=execution_timeout,
            ram_mem_mb=1000,
            ram_mem_mb_lmt=3000,
            *args,
            **kwargs,
        )
