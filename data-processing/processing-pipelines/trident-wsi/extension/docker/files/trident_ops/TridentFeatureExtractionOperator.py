from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION


class TridentFeatureExtractionOperator(KaapanaBaseOperator):
    """
    Runs TRIDENT's patch feature-extraction stage (trident.WSI.extract_patch_features)
    with a chosen foundation model, restricted to the patches computed by
    TridentPatchingOperator (i.e. only within the selected tissue region).

    :param dicom_operator: operator whose output dir holds the WSI's .dcm files.
    :param coords_operator: operator whose output dir holds TridentPatchingOperator's
        patch-coordinate h5.
    :param patch_encoder: any key from trident.patch_encoder_models.load.encoder_registry
        (e.g. "uni_v1", "uni_v2", "conch_v15", "gigapath", "virchow2", ...).
    :param hf_token: per-run HuggingFace token for gated model weights (NOT a shared
        platform secret - each user supplies their own; may be overridden at DAG-trigger
        time via the workflow_form "hf_token" field, see dag_trident_feature_extraction.py).
        Leave unset if the model's weights were baked into the image (see the trident
        processing-container's local_ckpts/ PoC bake-in path).
    """

    def __init__(
        self,
        dag,
        dicom_operator,
        coords_operator,
        patch_encoder: str = "uni_v2",
        hf_token: str = "",
        batch_limit: int = 64,
        name: str = "trident-feature-extraction",
        env_vars=None,
        execution_timeout=timedelta(minutes=90),
        **kwargs,
    ):
        if env_vars is None:
            env_vars = {}

        envs = {
            "TRIDENT_STAGE": "feat",
            "COORDS_IN_DIR": coords_operator.operator_out_dir,
            "PATCH_ENCODER": str(patch_encoder),
            "HF_TOKEN": str(hf_token),
            "BATCH_LIMIT": str(batch_limit),
        }
        env_vars.update(envs)

        if "labels" not in kwargs or not isinstance(kwargs["labels"], dict):
            kwargs["labels"] = {}
        # Foundation-model weight download from HuggingFace Hub needs outbound internet
        # whenever hf_token/PATCH_ENCODER isn't satisfied by a baked-in local checkpoint.
        kwargs["labels"]["network-access-external-ips"] = "true"

        super().__init__(
            dag=dag,
            name=name,
            input_operator=dicom_operator,
            image=f"{DEFAULT_REGISTRY}/trident:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            # Dev-cycle safeguard - see GeojsonToSROperator for why.
            image_pull_policy="Always",
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            enable_proxy=True,
            ram_mem_mb=16000,
            ram_mem_mb_lmt=32000,
            gpu_mem_mb=11000,
            retries=1,
            **kwargs,
        )
