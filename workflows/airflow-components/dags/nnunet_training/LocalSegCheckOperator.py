import os
import glob
import numpy as np
import nibabel as nib
import json

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalSegCheckOperator(KaapanaPythonBaseOperator):

    def get_nifti_dimensions(self,nifti_path):
        print("Loading NIFTI: {}".format(nifti_path))
        img = nib.load(nifti_path)
        data = img.get_fdata(dtype=np.float16)
        label_values = np.unique(data).astype(img.header.get_data_dtype())[1:]
    
    def get_dicom_dimensions(self):

    def start(self, ds, **kwargs):
        print("Split-Labels started..")

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folders = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

        print("Found {} batches".format(len(batch_folders)))

        for batch_element_dir in batch_folders:
            input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            output_dir = os.path.join(batch_element_dir, self.operator_out_dir)

            print("Search for NIFIs in {}".format(input_dir))
            batch_nifti_files = sorted(glob.glob(os.path.join(input_dir, "**", "*.nii*"), recursive=True))
            print("Found {} NIFTI files.".format(len(batch_nifti_files)))
            if len(batch_nifti_files) == 0:
                print("No NIFTI file was found!")
                print("abort!")
                exit(1)

            for nifti in batch_nifti_files:
                print("Loading labels...")
                label_names = self.get_labels_from_json(multilabel_dir=os.path.dirname(nifti))
                print("Loading NIFTI: {}".format(nifti))
                img = nib.load(nifti)
                data = img.get_fdata(dtype=np.float16)
                label_values = np.unique(data).astype(img.header.get_data_dtype())[1:]

                print("Found {} labels...".format(len(label_values)))
                if len(label_values) == 0:
                    print("No labels could be idenified!")
                    print("abort!")
                    exit(1)

                if len(label_values) > len(label_names):
                    print("There were more labels detected than label-names provided!")
                    print("abort!")
                    exit(1)

                print("Splitting multilabel into single NIFTI-files!")

                for label in label_values:
                    label_name = label_names[label]
                    tmp_mask = (data == label) * data
                    label_values = np.unique(tmp_mask).astype(img.header.get_data_dtype())
                    tmp_mask[tmp_mask == label] = 1

                    new_image = nib.nifti2.Nifti1Image(dataobj=tmp_mask.astype(img.header.get_data_dtype()), header=img.header, affine=img.affine)
                    # new_image = nib.nifti2.Nifti2Image(dataobj=tmp_mask.astype(header.get_data_dtype()),header=img.header,affine=img.affine)
                    print("Saving extracted mask {}: {}".format(label, label_name))
                    nib.save(new_image, os.path.join(output_dir, '{}.nii.gz'.format(label_name)))

                print("done")

    def __init__(self,
                 dag,
                 dicom_input_operator,
                 *args,
                 **kwargs):


        super().__init__(
            dag,
            name="check-seg-data",
            python_callable=self.start,
            *args,
            **kwargs
        )
