### For development

- git clone https://github.com/MIC-DKFZ/nnUNet.git
- Create mount path and run container forever with:

changes
    ...
    from kaapana.kubetools.volume_mount import VolumeMount
    from kaapana.kubetools.volume import Volume
    volume_mounts = [
        VolumeMount('nnunetdata', mount_path='/usr/local/lib/python3.9/site-packages/nnunet', sub_path=None, read_only=False)
    ]

    volumes = [
        Volume(name='nnunetdata', configs={
            'hostPath':
            {
                'type': 'DirectoryOrCreate',
                'path': '/home/ubuntu/dev/nnUNet/nnunet'
            }
        })
    ]

    nnunet_train = NnUnetOperator(
        ...
        cmds=["tail"],
        arguments=["-f", "/dev/null"], 
        volume_mounts=volume_mounts,
        volumes=volumes,
        ...
    )
    ...

z.B.:

    from kaapana.kubetools.volume_mount import VolumeMount
    from kaapana.kubetools.volume import Volume
    volume_mounts = [
        VolumeMount('nnunetdata', mount_path='/usr/local/lib/python3.9/site-packages/nnunet', sub_path=None, read_only=False),
        VolumeMount('srcdata', mount_path='/src', sub_path=None, read_only=False)
    ]

    volumes = [
        Volume(name='nnunetdata', configs={
            'hostPath':
            {
                'type': 'DirectoryOrCreate',
                'path': '/home/ubuntu/dev/nnUNet/nnunet'
            }
        }),
        Volume(name='srcdata', configs={
            'hostPath':
            {
                'type': 'DirectoryOrCreate',
                'path': '/home/ubuntu/dev/files'
            }
        })
    ]

    nnunet_train = NnUnetOperator(
        dag=dag,
        mode="training",
        train_max_epochs=max_epochs,
        input_operator=nnunet_preprocess,
        model=default_model,
        train_network_trainer=train_network_trainer,
        train_fold='all',
        retries=0,
        cmds=["tail"],
        arguments=["-f", "/dev/null"],
        volume_mounts=volume_mounts,
        volumes=volumes
    )