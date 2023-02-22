from kaapana.operators.KaapanaBaseOperator import default_registry, kaapana_build_version, KaapanaBaseOperator


class GenerateThumbnailOperator(KaapanaBaseOperator):
    """
    TODO!
    """

    def __init__(self,
                 dag,
                 orig_image_operator,
                 env_vars=None,
                 **kwargs
                 ):
        """
        :param target_filename: Only for packing. The created file.
        TODO
        """

        if env_vars is None:
            env_vars = {}

        envs = {
            "ORIG_IMAGE_OPERATOR_DIR": str(orig_image_operator.operator_out_dir),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{default_registry}/seg-thumbnail-generator:{kaapana_build_version}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            **kwargs
        )
