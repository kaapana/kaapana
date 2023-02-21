import os
from pathlib import Path
import glob
from datetime import timedelta
from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version, gpu_support


class mHubOperator(KaapanaBaseOperator):

    def pre_execute(self, context):
        print("++++++++++++++++++++++++++++ pre_execute operator")

    #     run_dir = os.path.join(self.workflow_dir, context['dag_run'].run_id)
    #     batch_folder = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, '*'))]

    #     if len(batch_folder) > 1:
    #         raise ValueError('This workflow can only be executed with one image')

    #     batch_element_dir  = batch_folder[0]

    #     self.volume_mounts.append(VolumeMount(
    #         'inputdata', mount_path='/app/data/input_data', sub_path=None, read_only=False
    #     ))


    #     self.volumes.append(
    #         Volume(name='inputdata', configs={
    #             'hostPath':
    #             {
    #                 'type': 'DirectoryOrCreate',
    #                 'path': os.path.join(
    #                     self.data_dir,
    #                     os.path.relpath(os.path.join(batch_element_dir), self.workflow_dir),
    #                     self.operator_in_dir
    #                     )
    #             }
    #         })
    #     )
    #     self.volume_mounts.append(VolumeMount(
    #         'outputdata', mount_path='/app/data/output_data', sub_path=None, read_only=False
    #     ))

    #     self.volumes.append(
    #         Volume(name='outputdata', configs={
    #             'hostPath':
    #             {
    #                 'type': 'DirectoryOrCreate',
    #                 'path': os.path.join(
    #                     self.data_dir,
    #                     os.path.relpath(os.path.join(batch_element_dir), self.workflow_dir),
    #                     self.operator_out_dir
    #                 )
    #             }
    #         })
    #     )
        
        if context['dag_run'].conf is not None and "workflow_form" in context['dag_run'].conf and "mhub_model" in context['dag_run'].conf["workflow_form"]:
            image = context['dag_run'].conf["workflow_form"]["mhub_model"]
        else:
            raise ValueError('You need to select a mhub_model!')

        if gpu_support:
            tag = 'cuda'
        else:
            tag = 'nocuda'
        # Tricking the CI to not check of image_name but still building all mhubai docker containers
        image_name=f"{default_registry}/mhubai-{image}-{tag}:{kaapana_build_version}"
        # self.image=f"{default_registry}/mhubai-platipy-cuda:{kaapana_build_version}"
        # self.image=f"{default_registry}/mhubai-platipy-nocuda:{kaapana_build_version}"
        # self.image=f"{default_registry}/mhubai-totalsegmentator-cuda:{kaapana_build_version}"
        # self.image=f"{default_registry}/mhubai-totalsegmentator-nocuda:{kaapana_build_version}"
        self.image = image_name
        print(f'Using the image {self.image}')

        super().pre_execute(context)

    def __init__(self,
                 dag,
                 name='mhub-operator',
                 execution_timeout=timedelta(minutes=300),
                 gpu_mem_mb=None,
                 *args, **kwargs
                 ):

        if gpu_support:
            gpu_mem_mb = 11000
            execution_timeout = timedelta(minutes=60)

        ram_mem_mb = 16000
        ram_mem_mb_lmt = 45000

        super().__init__(
            dag=dag,
            name=name,
            image_pull_secrets=["registry-secret"],
            ram_mem_mb=ram_mem_mb,
            ram_mem_mb_lmt=ram_mem_mb_lmt,
            gpu_mem_mb=gpu_mem_mb,
            execution_timeout=execution_timeout,
            *args,
            **kwargs
        )