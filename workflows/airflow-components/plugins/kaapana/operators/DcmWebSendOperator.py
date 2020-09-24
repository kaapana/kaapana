from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from datetime import timedelta

class DcmWebSendOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 ae_title='KAAPANA',
                 pacs_host='http://dcm4chee-service.store.svc',
                 pacs_port='8080',
                 env_vars=None,
                 execution_timeout=timedelta(minutes=5),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}
        
        envs = {
            "HOST": str(pacs_host),
            "PORT": str(pacs_port),
            "AETITLE": str(ae_title),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image="dktk-jip-registry.dkfz.de/processing-external/dicomwebsend:1.0.1-vdev",
            name="dcmweb-send",
            image_pull_secrets=["camic-registry"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            ram_mem_mb=300,
            gpu_mem_mb=None,
            *args, **kwargs
            )