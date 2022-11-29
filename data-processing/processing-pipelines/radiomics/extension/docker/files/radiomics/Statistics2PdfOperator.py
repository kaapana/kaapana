from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version
from datetime import timedelta

class Statistics2PdfOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(minutes=10),
                 **kwargs
                 ):

        super().__init__(
            dag=dag,
            image=f"{default_registry}/statistics2pdf:{kaapana_build_version}",
            name="stats2pdf",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            **kwargs
        )
