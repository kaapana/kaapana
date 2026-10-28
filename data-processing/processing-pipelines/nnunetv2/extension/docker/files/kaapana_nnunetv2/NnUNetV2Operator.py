from datetime import timedelta

from airflow.exceptions import AirflowSkipException
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator

# Resources follow nnU-Net's recommendations (documentation/installation_instructions.md): training needs a GPU
# with >= 10 GB and a strong CPU, "6 cores (12 threads) are the bare minimum", nnUNet_n_proc_DA=12 for an RTX 3090,
# 16 cores per GPU for fast GPUs such as the A100. Kaapana caps CPU at request + 100m unless a limit is given.
# gpu_mem_mb is the fallback; nnunetv2-train sets the reservation per run from the plans (kaapana_nnunetv2.gpu).
RESOURCES = {
    "create_dataset": dict(
        ram_mem_mb=8000, ram_mem_mb_lmt=32000, cpu_millicores=4000, cpu_millicores_lmt=8000, timeout=timedelta(hours=12)
    ),
    "plan_preprocess": dict(
        ram_mem_mb=16000, ram_mem_mb_lmt=64000, cpu_millicores=8000, cpu_millicores_lmt=12000, timeout=timedelta(days=1)
    ),
    "train": dict(
        ram_mem_mb=16000,
        ram_mem_mb_lmt=64000,
        cpu_millicores=12000,
        cpu_millicores_lmt=16000,
        gpu_mem_mb=11000,
        timeout=timedelta(days=7),
    ),
    "find_best_config": dict(
        ram_mem_mb=8000, ram_mem_mb_lmt=64000, cpu_millicores=4000, cpu_millicores_lmt=8000, timeout=timedelta(days=1)
    ),
    "predict": dict(
        ram_mem_mb=16000,
        ram_mem_mb_lmt=48000,
        cpu_millicores=4000,
        cpu_millicores_lmt=8000,
        gpu_mem_mb=6000,
        timeout=timedelta(hours=12),
    ),
    "refresh": dict(ram_mem_mb=1000, ram_mem_mb_lmt=4000, timeout=timedelta(hours=2)),
}
# prediction results are sent to Kaapana's DICOM receiver
LABELS = {"predict": {"network-access-ctp": "true"}}


class NnUNetV2Operator(KaapanaBaseOperator):
    """Runs one nnU-Net step (python -m kaapana_nnunet <step>) in one pod.

    The container reads the whole form from conf.json, fetches its inputs from the project bucket
    and publishes its outputs there; nothing is passed between tasks on disk.

    :param step: create_dataset, plan_preprocess, train, find_best_config, predict or refresh
    :param fold: (train) the fold this task trains; it is skipped unless the form selects it
    """

    def __init__(self, dag, step, fold=None, name=None, **kwargs):
        resources = dict(RESOURCES[step])
        timeout = resources.pop("timeout")
        self.step = step
        self.fold = fold
        env_vars = {"NNUNET_STEP": step}
        if fold is not None:
            env_vars["NNUNET_FOLD"] = str(fold)
        super().__init__(
            dag=dag,
            name=name or f"nnunet-{step.replace('_', '-')}" + (f"-fold-{fold}" if fold is not None else ""),
            image=f"{DEFAULT_REGISTRY}/nnunetv2:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            labels=dict(LABELS.get(step, {})),
            execution_timeout=timeout,
            retries=0,
            **resources,
            **kwargs,
        )

    def execute(self, context):
        if self.fold is not None:
            folds = (context["dag_run"].conf or {}).get("workflow_form", {}).get("folds") or []
            if str(self.fold) not in [str(f) for f in folds]:
                raise AirflowSkipException(f"fold {self.fold} not selected")
        # the caching decorator of KaapanaBaseOperator.execute only accepts context as keyword
        return super().execute(context=context)
