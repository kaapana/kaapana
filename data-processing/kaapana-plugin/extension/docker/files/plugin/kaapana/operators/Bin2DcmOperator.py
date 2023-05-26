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


class Bin2DcmOperator(KaapanaBaseOperator):
    """
    Operator to encode binary data into DICOM or to decode binary data from DICOM.

    This operator encodes or decodes files using a container.
    The container uses the dcmtk tool xml2dcm https://support.dcmtk.org/docs/xml2dcm.html
    Binary files can be split up in chunks of a specific size [size_limit]

    **Inputs:**

    * The input_operator
    * When decoding: file_extension .dcm
    * When encoding: file_extensions, size_limit and additional encoded string parameters

    **Outputs:**

    * When encoding: DICOM files
    * When decoding: binary file (e.g. zip-file)
    """

    execution_timeout = timedelta(minutes=10)

    def __init__(
        self,
        dag,
        dataset_info_operator=None,
        dataset_info_operator_in_dir=None,
        file_extensions="*.zip",
        size_limit=100,
        patient_id="",
        patient_name="",
        protocol_name="",
        instance_name="N/A",
        version="0.0.0",
        manufacturer="KAAPANA",
        manufacturer_model="bin2dcm",
        study_description=None,
        series_description=None,
        study_id="bin2dcm",
        study_uid=None,
        name="bin2dcm",
        env_vars={},
        execution_timeout=execution_timeout,
        **kwargs,
    ):
        """
        :param dataset_info_operator: Only encoding. Input operator producing dataset.json as output.
        :param dataset_info_operator_in_dir: Only encoding. Directory with a dataset.json file used in study_description.
        :param file_extensions: for decoding *.dcm, for encoding list of extensions to include seperated by ',' eg:  "*.zip,*.bin"
        :param size_limit: Only for decoding. Allows to split up the binary in chunks of a specific size in bytes.
        :param patient_id: Only for decoding. Name written in DICOM tag.
        :param patient_name: Only for decoding. Name written in DICOM tag.
        :param protocol_name: Only for decoding. Name written in DICOM tag.
        :param instance_name: Only for decoding. Name written in DICOM tag.
        :param version: Only for decoding. Name written in DICOM tag.
        :param manufacturer: Only for decoding. Name written in DICOM tag.
        :param manufacturer_model: Only for decoding. Name written in DICOM tag.
        :param study_description: Only for decoding. Name written in DICOM tag.
        :param series_description: Only for decoding. Name written in DICOM tag.
        :param study_id: Only for decoding. Name written in DICOM tag.
        :param study_uid: Only for decoding. Name written in DICOM tag.
        """

        if dataset_info_operator_in_dir is None:
            dataset_info_operator_in_dir = (
                dataset_info_operator.operator_out_dir
                if dataset_info_operator is not None
                else ""
            )

        envs = {
            "DATASET_INFO_OPERATOR_DIR": dataset_info_operator_in_dir,
            "STUDY_ID": str(study_id),
            "STUDY_UID": str(study_uid),
            "STUDY_DESCRIPTION": str(study_description),
            "SERIES_DESCRIPTION": str(series_description),
            "PATIENT_NAME": str(patient_name),
            "PATIENT_ID": str(patient_id),
            "INSTANCE_NAME": str(instance_name),
            "MANUFACTURER": str(manufacturer),
            "MANUFACTURER_MODEL": str(manufacturer_model),
            "VERSION": str(version),
            "PROTOCOL_NAME": str(protocol_name),
            "SIZE_LIMIT_MB": str(size_limit),
            "EXTENSIONS": file_extensions,
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/bin2dcm:{KAAPANA_BUILD_VERSION}",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            keep_parallel_id=False,
            env_vars=env_vars,
            ram_mem_mb=5000,
            **kwargs,
        )
