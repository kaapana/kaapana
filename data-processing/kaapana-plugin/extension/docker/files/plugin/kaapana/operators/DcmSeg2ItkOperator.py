from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version
from datetime import timedelta

class DcmSeg2ItkOperator(KaapanaBaseOperator):
    """
        Operator converts .dcm segmentation data into other file formats.
        
        This operator takes a .dcm segmentation file and creates a segmentation file in a different file format e.g. .nrrd file format.
        The operator uses the dcmqi libary.
        For dcmqi documentation please have a look at https://qiicr.gitbook.io/dcmqi-guide/.
        
        **Inputs:**
        * .dcm segmentation file

        **Outputs:**
        * segmentation file in a file format specified by output_format
    """
    def __init__(self,
                 dag,
                 output_format=None,
                 seg_filter=None,
                 env_vars=None,
                 execution_timeout=timedelta(minutes=90),
                 **kwargs
                 ):
        """
        :param output_format: File format of the created segmentation file
           If not specified "nrrd"
        :param seg_filter: A bash list of organs, that should be filtered from the segmentation e.g. "liver,aorta"
        :param env_vars: Environmental variables
        :param execution_timeout: max time allowed for the execution of this task instance, if it goes beyond it will raise and fail
        """

        if env_vars is None:
            env_vars = {}

        envs = {
            "OUTPUT_TYPE": output_format or 'nrrd',
            "SEG_FILTER": seg_filter or '', # a bash list i.e.: 'liver,aorta'
            "DCMQI_COMMAND": "segimage2itkimage",
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{default_registry}/dcmqi:{kaapana_build_version}",
            name="dcmseg2nrrd",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=3000,
            ram_mem_mb_lmt=20000,
             **kwargs
            )
