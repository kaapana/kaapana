import os
from pathlib import Path
import glob
from datetime import timedelta
from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION, GPU_SUPPORT


class mHubOperator(KaapanaBaseOperator):

    def pre_execute(self, context):
        print("++++++++++++++++++++++++++++ pre_execute operator")
        
        if context['dag_run'].conf is not None and "workflow_form" in context['dag_run'].conf and "mhub_model" in context['dag_run'].conf["workflow_form"]:
            image = context['dag_run'].conf["workflow_form"]["mhub_model"]
        else:
            raise ValueError('You need to select a mhub_model!')

        if GPU_SUPPORT:
            tag = 'cuda'
        else:
            tag = 'nocuda'
        # Tricking the CI to not check of image_name but still building all mhubai docker containers
        image_name=f"{DEFAULT_REGISTRY}/mhubai-{image}-{tag}:{KAAPANA_BUILD_VERSION}"
        # self.image=f"{DEFAULT_REGISTRY}/mhubai-platipy-cuda:{KAAPANA_BUILD_VERSION}"
        # self.image=f"{DEFAULT_REGISTRY}/mhubai-platipy-nocuda:{KAAPANA_BUILD_VERSION}"
        # self.image=f"{DEFAULT_REGISTRY}/mhubai-totalsegmentator-cuda:{KAAPANA_BUILD_VERSION}"
        # self.image=f"{DEFAULT_REGISTRY}/mhubai-totalsegmentator-nocuda:{KAAPANA_BUILD_VERSION}"
        self.image = image_name
        print(f'Using the image {self.image}')

        self.env_vars.update({
            "MHUB_MODEL": image,
        })

        super().pre_execute(context)

    def __init__(self,
                dag,
                name='mhub-operator',
                cmds=["bash"],
                arguments=["/kaapana/mounted/workflows/mounted_scripts/mhub/mhub.sh"],
                execution_timeout=timedelta(minutes=300),
                gpu_mem_mb=None,
                *args, **kwargs
                ):

        if GPU_SUPPORT:
            gpu_mem_mb = 11000
            execution_timeout = timedelta(minutes=60)

        ram_mem_mb = 16000
        ram_mem_mb_lmt = 45000

        super().__init__(
            dag=dag,
            name=name,
            image_pull_secrets=["registry-secret"],
            cmds=cmds,
            arguments=arguments,
            ram_mem_mb=ram_mem_mb,
            ram_mem_mb_lmt=ram_mem_mb_lmt,
            gpu_mem_mb=gpu_mem_mb,
            execution_timeout=execution_timeout,
            *args,
            **kwargs
        )