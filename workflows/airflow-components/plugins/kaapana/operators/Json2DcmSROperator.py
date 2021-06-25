from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project, default_registry, default_project
from datetime import timedelta

class Json2DcmSROperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 src_dicom_operator = None, 
                 seg_dicom_operator = None, 
                 input_file_extension = "*.json", # *.json or eg measurements.json
                 env_vars=None,
                 execution_timeout=timedelta(minutes=90),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "INPUT_FILE_EXTENSION": input_file_extension,
            "SRC_DICOM_OPERATOR": str(src_dicom_operator.operator_out_dir) if src_dicom_operator is not None else "None",
            "SEG_DICOM_OPERATOR": str(seg_dicom_operator.operator_out_dir) if seg_dicom_operator is not None else "None",
            "DCMQI_COMMAND": "tid1500writer",
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{default_registry}/dcmqi:v1.2.4-vdev",
            name="json2dcmSR",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=1000,
            *args, **kwargs
            )
