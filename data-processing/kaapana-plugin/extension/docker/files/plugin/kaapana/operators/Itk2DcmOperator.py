from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class Itk2DcmOperator(KaapanaBaseOperator):
    """
    Operator which converts nifti files to dicom files. 

    **Inputs:**
        Nifti files in a dataset directory structure specified by the nnU-Net project (https://github.com/MIC-DKFZ/nnUNet)
        
        Unimodal datasets can also be parsed directly with the following structure.

        path
        |----dataset
        |    | meta_data.json
        |    | seg_info.json
        |    | series1.nii.gz
        |    | series1_seg.nii.gz
        |    | series2.nii.gz
        |    | series2_seg.nii.gz
        |    | ...

    **Outputs:**
        Converted Dicoms. Associated segmentations are not converted yet, but prepared to be converted by the Itk2DcmSegOperator. 
    """
    def __init__(
        self, dag, name=None, execution_timeout=timedelta(minutes=90), *args, **kwargs
    ) -> None:
        name = name if name is not None else "itk2dcm-converter"

        super().__init__(
            dag=dag,
            name=name,
            image=f"{DEFAULT_REGISTRY}/itk2dcm:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=6000,
            ram_mem_mb_lmt=12000,
            *args,
            **kwargs,
        )
