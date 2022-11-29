import os
from datetime import timedelta
from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version


class DcmModifyOperator(KaapanaBaseOperator):
    """
    Operator to modify DICOM tags.

    This operator serves to modify DICOM tags of DICOM files.
    The opartor relies on DCMTK's "dcmodify" function.

    **Inputs:**

    * DICOM files which should be modified.
    * DICOM tags which should be modified in given DICOM files.

    **Outputs:**

    * Modified DICOM files according to DICOM tags.
    """

    execution_timeout = timedelta(seconds=60)

    def __init__(self,
                 dag,
                 dicom_tags_to_modify, # eg: "(0008,0016)=1.2.840.10008.5.1.4.1.1.88.11;(0008,0017)=1.2.840.10008.5.1.4.1.1.88.11;(0008,0018)=1.2.840.10008.5.1.4.1.1.88.11"
                 name="DcmModify",
                 env_vars={},
                 execution_timeout=execution_timeout,
                 **kwargs
                 ):
        """
        :param dicom_tags_to_modify: List of all DICOM tags which should be modified in given DICOM file. Specify using the following syntax: eg: "(0008,0016)=1.2.840.10008.5.1.4.1.1.88.11;(0008,0017)=1.2.840.10008.5.1.4.1.1.88.11; ... .
        """

        envs = {
            "DICOM_TAGS_TO_MODIFY": str(dicom_tags_to_modify),
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{default_registry}/dcmodify:{kaapana_build_version}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            keep_parallel_id=False,
            env_vars=env_vars,
            ram_mem_mb=100,
            **kwargs
        )
