from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from datetime import timedelta

class DcmWebSendOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 ae_title='KAAPANA',
                 pacs_origin= 'http://ctp-service.flow.svc',
                 pacs_port='7777',
                 env_vars=None,
                 execution_timeout=timedelta(minutes=10),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}
        
        envs = {
            "PACS_ORIGIN": str(pacs_origin),
            "PORT": str(pacs_port),
            "AETITLE": str(ae_title),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image="{}{}/dicomwebsend:0.50.0".format(default_registry, default_project),
            name="dcmweb-send",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            ram_mem_mb=300,
            gpu_mem_mb=None,
            *args, **kwargs
            )