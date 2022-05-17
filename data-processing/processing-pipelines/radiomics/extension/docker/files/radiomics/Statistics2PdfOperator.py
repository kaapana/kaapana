from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from datetime import timedelta

class Statistics2PdfOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(minutes=10),
                 **kwargs
                 ):

        super().__init__(
            dag=dag,
            image=f"{default_registry}/statistics2pdf:0.1.0",
            name="stats2pdf",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            **kwargs
        )
