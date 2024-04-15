import os
from datetime import timedelta
from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


class DcmModifyOperator(KaapanaBaseOperator):
    """
    Operator to modify DICOM tags.

    This operator serves to modify DICOM tags of DICOM files.
    The operator relies on DCMTK's "dcmodify" function.

    Note: This operator edits the DICOM files in-place. Therefore, the original DICOM files are modified.
    Furthermore, it creates a backup of the original DICOM files in the same directory with ending "{filename}.bak".
    If the filename ends with ".dcm", the backup file will be named "{filename}.dcm.bak".

    **Inputs:**

    * DICOM files which should be modified.
    * DICOM tags which should be modified in given DICOM files.

    **Outputs:**

    * Modified DICOM files according to DICOM tags.
    """

    def __init__(
        self,
        dag,
        dicom_tags_to_modify,  # eg: "(0008,0016)=1.2.840.10008.5.1.4.1.1.88.11;(0008,0017)=1.2.840.10008.5.1.4.1.1.88.11;(0008,0018)=1.2.840.10008.5.1.4.1.1.88.11"
        name="DcmModify",
        env_vars={},
        **kwargs,
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
            image=f"{DEFAULT_REGISTRY}/dcmodify:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            keep_parallel_id=False,
            env_vars=env_vars,
            ram_mem_mb=100,
            **kwargs,
        )
