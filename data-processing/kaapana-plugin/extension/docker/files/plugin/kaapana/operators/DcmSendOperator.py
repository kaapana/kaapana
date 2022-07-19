from datetime import timedelta, datetime

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, \
    default_registry, default_platform_abbr, default_platform_version


class DcmSendOperator(KaapanaBaseOperator):
    """
    Operator sends data to the platform.

    This operator is used for sending data to the platform.
    For dcmsend documentation please have a look at https://support.dcmtk.org/docs/dcmsend.html.
    """

    def __init__(self,
                 dag,
                 name: str = "dcmsend",
                 ae_title: str = "NONE",
                 pacs_host: str = "ctp-dicom-service.flow.svc",
                 pacs_port: str = "11112",
                 env_vars=None,
                 level: str = "element",
                 check_arrival: bool = False,
                 execution_timeout: datetime = timedelta(minutes=60),
                 **kwargs
                 ):

        """
        :param ae_title: calling Application Entity (AE) title
        :param pacs_host: Host of PACS
        :param pacs_port: Port of PACS
        :param env_vars: Environment variables
        :param level: "element" or "batch"
            If batch, an operator folder next to the batch folder with .dcm files is expected.
            If element, *.dcm are expected in the corresponding operator with .dcm files is expected.
        :param check_arrival: Verifies if data transfer was successful
        :param execution_timeout: timeout for connection requests
        """

        if level not in ["element", "batch"]:
            raise NameError("level must be either 'element' or 'batch'. If batch, an operator folder next to the batch folder with .dcm files is expected. If element, *.dcm are expected in the corresponding operator with .dcm files is expected.")

        if env_vars is None:
            env_vars = {}

        envs = {
            "HOST": str(pacs_host),
            "PORT": str(pacs_port),
            "AETITLE": str(ae_title),
            "CHECK_ARRIVAL": str(check_arrival),
            "LEVEL": str(level)
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name=name,
            image=f"{default_registry}/dcmsend:{default_platform_abbr}_{default_platform_version}__3.6.4",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            **kwargs
        )
