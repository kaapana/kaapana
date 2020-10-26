from datetime import timedelta


from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project


class TemplateExecPythonOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(minutes=15),
                 *args, **kwargs
                 ):

        super().__init__(
            dag=dag,
            name='temp-exec-python',
            image="{}{}/python-template:0.1.0".format(default_registry, default_project),
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            *args,
            **kwargs
        )

