from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class PyradiomicsExtractorOperator(KaapanaBaseOperator):
    def __init__(
        self,
        dag,
        name="pyradiomics-feature-extractor",
        feature_class_prop_key="feature_classes",  # the key inside the DAG UI form that specifies the selected feature classes
        env_vars={},  # environment variables that will be passed inside the container
        execution_timeout=timedelta(hours=6),
        *args,
        **kwargs,
    ):
        # pass the property key in UI forms for feature classes as env var
        envs = {
            "FEATURE_CLASS_PROP_KEY": feature_class_prop_key,
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name=name,
            image=f"localhost:32000/pyradiomics-extract-features:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            image_pull_policy="IfNotPresent",  # either 'Always' or 'IfNotPresent'. If set to Always, k8s always tries to pull the image from registry
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            ram_mem_mb=5000,
            *args,
            **kwargs,
        )
