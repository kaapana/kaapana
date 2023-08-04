from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class Json2DcmSROperator(KaapanaBaseOperator):
    """
    Operator to generate DICOM Structured Reports.

    This operator extracts information given by input json-files, dicom-files and dicom-seg-files.
    The extracted information is collected in a tid_template downloaded from https://raw.githubusercontent.com/qiicr/dcmqi/master/doc/schemas/sr-tid1500-schema.json# .
    The modified tid_template is then passed to DCMQI's tid1500writer which converts and saves the previously extracted and summarized information into a DICOM Structured Report following the template TID1500.
    Furter information about DCMQI's tid1500writer: https://qiicr.gitbook.io/dcmqi-guide/opening/cmd_tools/sr/tid1500writer

    **Inputs:**

    * src_dicom_operator: Input operator which provides the processed DICOM file.
    * seg_dicom_operator: Input operator which provides the processed DICOM_SEG file.
    * input_file_extension: ".json" by default

    ***Outputs:**

    * DcmSR-file: .dcm-file which contains the DICOM Structured Report.

    """

    def __init__(
        self,
        dag,
        src_dicom_operator=None,
        seg_dicom_operator=None,
        input_file_extension="*.json",  # *.json or eg measurements.json
        env_vars=None,
        execution_timeout=timedelta(minutes=90),
        **kwargs,
    ):
        """
        :param dag: DAG in which the operator is executed.
        :param src_dicom_operator: Input operator which provides the processed DICOM file.
        :param seg_dicom_operator: Input operator which provides the processed DICOM_SEG file.
        :param input_file_extension: ".json" by default
        """

        if env_vars is None:
            env_vars = {}

        envs = {
            "INPUT_FILE_EXTENSION": input_file_extension,
            "SRC_DICOM_OPERATOR": str(src_dicom_operator.operator_out_dir)
            if src_dicom_operator is not None
            else "None",
            "SEG_DICOM_OPERATOR": str(seg_dicom_operator.operator_out_dir)
            if seg_dicom_operator is not None
            else "None",
            "DCMQI_COMMAND": "tid1500writer",
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/dcmqi:{KAAPANA_BUILD_VERSION}",
            name="json2dcmSR",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=1000,
            **kwargs,
        )
