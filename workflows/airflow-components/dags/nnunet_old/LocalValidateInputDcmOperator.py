import os
import glob
import numpy as np
import nibabel as nib

from nnunet.getTaskInfo import get_task_info
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalValidateInputDcmOperator(KaapanaPythonBaseOperator):

    def validate(input_dir):
        dicom_dir = os.path.join(batch_element_dir, 'initial-input')
        print("Start validating: {}".format(dicom_dir))
        dcm_files = sorted(glob.glob(os.path.join(dicom_dir, "*.dcm"), recursive=True))

        if len(dcm_files) == 0:
            print("No dicom file found! -> validation not possible -> abort!")
            exit(1)

        dcm_file = pydicom.dcmread(dcm_files[0])
        dcm_modality = dcm_file[0x0008, 0x0060].value
        dcm_series_description = dcm_file[0x0008, 0x103e].value
        dcm_series_code = dcm_file[0x0008, 0x103f].value
        dcm_body_part = dcm_file[0x0018, 0x0015].value

        print("dcm_modality: {}".format(dcm_modality))
        print("dcm_series_description: {}".format(dcm_series_description))
        print("dcm_series_code: {}".format(dcm_series_code))
        print("dcm_body_part: {}".format(dcm_body_part))

        if validate_modality:
            if dcm_modality in task_modalities:
                print("Found input modality: {}".format(dcm_modality))
            else:
                print("Wrong input-modality!")
                print("Found: {}".format(dcm_modality))
                print("Expected: {}".format(task_modalities))
                print("Abort!")
                exit(1)

        if validate_body_part:
            if dcm_body_part == task_body_part:
                print("Found input body_part: {}".format(dcm_body_part))
            else:
                print("Wrong input-body-part!")
                print("Found: {}".format(dcm_body_part))
                print("Expected: {}".format(task_body_part))
                print("Abort!")
                exit(1)

        if validate_protocol:
            if dcm_series_code in task_protocolls:
                print("Found input protocol: {}".format(dcm_series_code))
            else:
                print("Wrong input-protocol!")
                print("Found: {}".format(dcm_series_code))
                print("Expected: {}".format(task_protocolls))
                print("Abort!")
                exit(1)

    def start(self, ds, **kwargs):
        print("Starting LocalValidateInputDcmOperator...")
        print(kwargs)

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_dirs = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

        for batch_element_dir in batch_dirs:
            input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            output_dir = os.path.join(batch_element_dir, self.operator_out_dir)

    def __init__(self,
                 dag,
                 label_names=None,
                 task=None,
                 *args,
                 **kwargs):

        if (label_names == None and task == None) or (label_names != None and task != None):
            print("Either 'label_names' OR 'task' has to be specified!")
            print("Abort.")
            exit(1)

        if task != None:
            self.label_names = get_task_info(task)["organs"].split(";").insert(0, "empty")
        else:
            self.label_names = label_names

        super().__init__(
            dag,
            name="split-labels",
            python_callable=self.start,
            *args, **kwargs
        )
