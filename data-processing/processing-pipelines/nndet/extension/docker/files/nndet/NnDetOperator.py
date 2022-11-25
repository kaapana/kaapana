from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version
from datetime import timedelta
from dataclasses import dataclass
from enum import Enum

class Mode(Enum):
    INFERENCE = "inference"
    
    def __str__(self):
        return self.value
    
    
@dataclass
class NnDetParams:
    det_models: str = "/models/nnDet"
    det_data: str = "/det_data"
    ntta: str = "1"
    no_preprocess = "0"


class NnDetOperator(KaapanaBaseOperator):
    """
    nnDetection operator: simultaneous localization and categorization of objects in medical images (medical object detection)
    
    Code: https://github.com/MIC-DKFZ/nnDetection
    Paper: https://doi.org/10.1007/978-3-030-87240-3_51
    
    **Inputs:**

    * Data in nifti format
    
    **Outputs:**
    
    * pkl file "<case>_boxes.pkl": contains a dictonary with keys: 'pred_boxes', 'pred_scores', 'pred_labels', 'restore', 'original_size_of_raw_data', 'itk_origin', 'itk_spacing'
    * mask "<case>_boxes.nii.gz: nii.gz with overlapping bounding boxes
    """
    
    execution_timeout = timedelta(days=5)
    task_dict = {}
    
    def __init__(self,
                 dag,
                 mode: Mode,
                 name="nndet",
                 nndet_params: NnDetParams=NnDetParams(),
                 env_vars={},
                 parallel_id=None,
                 execution_timeout=execution_timeout,
                 **kwargs
                 ):
        envs = {"MODE": str(mode),
                "det_models": nndet_params.det_models,
                "det_data": nndet_params.det_data,
                "NTTA": nndet_params.ntta,
                "NO_PREPROCESS": nndet_params.no_preprocess
                }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{default_registry}/nndet-gpu:{kaapana_build_version}",
            name=name,
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=16000,
            ram_mem_mb_lmt=45000,
            gpu_mem_mb=5000,
            env_vars=env_vars,
            **kwargs
        )