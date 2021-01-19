from kaapana.kubetools.resources import Resources as PodResources
from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from ct_pet_prediction.KaapanaBaseOperator import KaapanaBaseOperator
from datetime import timedelta


class CtPetPredictionTrainingOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(days=2)

    def __init__(self,
                 dag,
                 cpu_count=20,
                 lr=0.0003,
                 batch_size=4,
                 dropout=0.25,
                 epochs=50,
                 device='cuda:0',
                 model='UNet3d',
                 patch_size=(96, 96, 96),
                 patience=15,
                 resume='',
                 channels='1',
                 tb_info='',
                 env_vars=None,
                 parallel_id=None,
                 execution_timeout=execution_timeout,
                 *args,
                 **kwargs):

        if env_vars is None:
            env_vars = {}

        envs = {
            "LR": str(lr),
            "CPU_COUNT": str(cpu_count),
            "BATCH_SIZE": str(batch_size),
            "DROPOUT": str(dropout),
            "EPOCHS": str(epochs),
            "DEVICE": str(device),
            "MODEL": str(model),
            "PATCH_SIZE": str(patch_size),
            "PATIENCE": str(patience),
            "RESUME": str(resume),
            "CHANNELS": str(channels),
            "TB_INFO": str(tb_info),
            "TENSORBOARD_DIR": '/tensorboard',
        }
        env_vars.update(envs)

        volume_mounts = []
        volumes = []

        volume_mounts.append(VolumeMount(
            'dshm', mount_path='/dev/shm', sub_path=None, read_only=False))
        volume_config = {
            'emptyDir':
            {
                'medium': 'Memory',
            }
        }
        volumes.append(Volume(name='dshm', configs=volume_config))

        pod_resources = PodResources(request_memory=None, request_cpu=None,limit_memory=None, limit_cpu=None, limit_gpu=1)
        super(CtPetPredictionTrainingOperator, self).__init__(
            dag=dag,
            image="dktk-jip-registry.dkfz.de/ctpet/ctpet-training:0.4-vdev",
            name="training",
            training_operator=True,
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            image_pull_policy="Always",
            volumes=volumes,
            volume_mounts=volume_mounts,
            execution_timeout=execution_timeout,
            pod_resources=pod_resources,
            env_vars=env_vars,
            ram_mem_mb=9000,
            ram_mem_mb_lmt=10000,
            gpu_mem_mb=None,
            *args,
            **kwargs)
