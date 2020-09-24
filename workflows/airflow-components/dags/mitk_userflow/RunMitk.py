from datetime import timedelta, datetime
import os
import uuid
import glob
from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.operators.KaapanaApplicationBaseOperator import KaapanaApplicationBaseOperator

class RunMitk(KaapanaApplicationBaseOperator):

    def __init__(self,
                 dag,
                 data_operator=None,
                 execution_timeout=timedelta(minutes=60),
                 env_vars=None,
                 *args,**kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        ingress_path = "/dynamic-mitk-segmentation-" + datetime.now().strftime("%d-%b-%Y-%H-%M-%S")
        print(ingress_path)

        envs = {
            "INGRESS_PATH": ingress_path,
            "USER":"mitk",
            "PASSWORD":"mitk"
            #"RESOLUTION": "1920x1080",
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name="mitk",
            image="dktk-jip-registry.dkfz.de/kaapana/mitk-vnc:1-vdev",
            input_operator=data_operator,
            image_pull_secrets=["camic-registry"],
            service=True,
            ingress=True,
            execution_timeout=execution_timeout,
            startup_timeout_seconds=500,
            port=80,
            ingress_path=ingress_path,
            env_vars=env_vars,
            *args,
            **kwargs)
