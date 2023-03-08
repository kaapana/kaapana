import os
import glob
from datetime import timedelta
import pydicom

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION


class Pdf2DcmOperator(KaapanaBaseOperator):
    """
    Operator saves DICOM meta information in a DICOM Encapsulated PDF Storage SOP instance.

    This operator either takes DICOM meta information or reads the DICOM meta information from existing DICOM files.
    The DICOM meta information are converted to a DICOM Encapsulated PDF Storage SOP instance and are stored in a specified ouput directory.
    The converting process is done by DCMTK's pdf2dcm function: https://support.dcmtk.org/docs/pdf2dcm.html .

    **Inputs:**
    * (either) PDF file containing all DICOM meta information
    * (or) DICOM file to extract DICOM meta information from

    **Outputs:**
    * DICOM Encapsulated PDF Storage SOP instance containing the extracted DICOM meta information
    """

    def __init__(self,
                 dag,
                 pdf_title='KAAPANA PDF',
                 dicom_operator = None,
                 aetitle=None,
                 study_uid=None,
                 study_description=None,
                 patient_id=None,
                 patient_name=None,
                 env_vars=None,
                 execution_timeout=timedelta(minutes=10),
                 **kwargs
                 ):

        """
        :param pdf_title: Title of PDF file that is DICOM encapsulated.
        :dicom_operator: Used to find DICOM files from which DICOM meta information is extracted.
        :aetitle: DICOM meta information.
        :study_uid: DICOM meta information.
        :study_description: DICOM meta information.
        :patient_id: DICOM meta information.
        :patient_name: DICOM meta information.
        :env_vars: Dictionary to store environmental variables.
        :execution_timeout:
        """

        if env_vars is None:
            env_vars = {}

        envs = {
            "AETITLE": str(aetitle),
            "STUDY_UID": str(study_uid),
            "STUDY_DES": str(study_description),
            "PAT_ID": str(patient_id),
            "PAT_NAME": str(patient_name),
            "PDF_TITLE": str(pdf_title),
            "DICOM_IN_DIR": str(dicom_operator.operator_out_dir) if dicom_operator is not None else str(None),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/pdf2dcm:{KAAPANA_BUILD_VERSION}",
            name="pdf2dcm",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            **kwargs
        )
