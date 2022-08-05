from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_platform_abbr, default_platform_version
from datetime import timedelta


class DcmConverterOperator(KaapanaBaseOperator):
    """
    Operator to convert dcm files to nrrd or nii.gz files.

    This operator converts incoming DICOM (dcm) files to nrrd or NIFTI (nii.gz) files.
    By dafult, the files are converted to nrrd file format.
    The conversion operation is executed using MITK's FileConverter.
    """

    def __init__(self,
                 dag,
                 output_format="nrrd",
                 parallel_processes=3,
                 env_vars=None,
                 execution_timeout=timedelta(hours=10),
                 **kwargs
                 ):
        """
        :param output_format: File format to which the incoming DICOM files are converted to. Possible values: "nrrd" (default), nii.gz, nii
        :parallel_processes: Defines how many processes are executed in parallel (default: 3)
        """

        if env_vars is None:
            env_vars = {}

        envs = {
            "CONVERTTO": output_format,
            "THREADS": str(parallel_processes),
        }

        env_vars.update(envs)

        if output_format != "nrrd" and (output_format != "nii.gz" and output_format != "nii"):
            print(("output format %s is currently not supported!" % output_format))
            print("Dcm2nrrdOperator options: 'nrrd' or 'nii'")
            raise ValueError('ERROR')

        super().__init__(
            dag=dag,
            image=f"{default_registry}/mitk-fileconverter:{default_platform_abbr}_{default_platform_version}__2021-02-18-fix",
            name='dcm-converter',
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=2000,
            ram_mem_mb_lmt=12000,
             **kwargs
        )
