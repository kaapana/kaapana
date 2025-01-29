from datetime import datetime, timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class DcmSendOperator(KaapanaBaseOperator):
    """
    Operator sends data to the platform.

    This operator is used for sending data to the platform.
    """

    def __init__(
        self,
        dag,
        name: str = "dcmsend",
        calling_ae_title_scu: str = "",
        called_ae_title_scp: str = "",
        pacs_host: int = "",
        pacs_port: str = "",
        env_vars: dict = {},
        execution_timeout: datetime = timedelta(minutes=60),
        **kwargs,
    ):
        """
        :param calling_ae_title_scu: Local Calling AET. Kaapana interprets this as the dataset name.
        :param called_ae_title_scp: Remote Called AET. Kaapana interprets this as the project name.
        :param pacs_host: Host of PACS
        :param pacs_port: Port of PACS
        :param env_vars: Environment variables
        :param execution_timeout: timeout for connection requests
        """

        env_vars.update(
            {
                "PACS_HOST": str(pacs_host),
                "PACS_PORT": str(pacs_port),
                "CALLING_AE_TITLE_SCU": str(calling_ae_title_scu),
                "CALLED_AE_TITLE_SCP": str(called_ae_title_scp),
            }
        )

        if not kwargs.get("labels"):
            kwargs["labels"] = {}
            kwargs["labels"]["network-access"] = "ctp"

        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/dcmsend:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            **kwargs,
        )
