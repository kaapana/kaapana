    

from datetime import datetime, timedelta
import os
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class SendIncomingEmailOperator(KaapanaBaseOperator):

    def __init__(
        self,
        dag,
        name: str = "send-incoming-email",
        env_vars=None,
        execution_timeout: datetime = timedelta(minutes=60),
        **kwargs,
    ):
        """
        """

        if env_vars is None:
            env_vars = {}

        smtp_host = os.getenv("SMTP_HOST", None)
        smtp_port = os.getenv("SMTP_PORT", 0)
        sender = os.getenv("EMAIL_ADDRESS_SENDER", None)
        smtp_username = os.getenv("SMTP_USERNAME", None)
        smtp_password = os.getenv("SMTP_PASSWORD", None)
        email_receiver = os.getenv("EMAIL_RECEIVER", "")
        envs = {

            "SMTP_HOST": str(smtp_host),
            "SMTP_PORT": str(smtp_port),
            "EMAIL_ADDRESS_SENDER": str(sender),
            "SMTP_USERNAME": str(smtp_username),
            "SMTP_PASSWORD": str(smtp_password),
            "EMAIL_RECEIVER": str(email_receiver),
        }

        env_vars.update(envs)

        if "labels" not in kwargs or not isinstance(kwargs["labels"], dict):
            kwargs["labels"] = {}

        kwargs["labels"]["network-access-external-ips"] = "true"

        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/send-incoming-email:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            ram_mem_mb=50,
            ram_mem_mb_lmt=4000,
            **kwargs,
        )
