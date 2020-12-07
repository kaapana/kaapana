import os
import glob
import numpy as np
import nibabel as nib
import json

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalSplitLabelOperator(KaapanaPythonBaseOperator):

    def get_labels_from_json(self, multilabel_dir):
        labels_json_path = os.path.join(multilabel_dir, self.labels_json)
        if not os.path.isfile(labels_json_path):
            print("Could not find labels-json!")
            print("Path: {}".format(labels_json_path))
            print("abort.")
            exit(1)

        else:
            with open(labels_json_path) as f:
                labels_dict = json.load(f)

                if "labels" not in labels_dict:
                    print("Wrong labels-json!")
                    print("Could not find key 'labels' in {}".format(labels_json_path))
                    print("abort.")
                    exit(1)
                elif not isinstance(labels_dict["labels"], list):
                    print("Wrong labels-json!")
                    print("Could key 'labels' need a list as value! file: {}".format(labels_json_path))
                    print("abort.")
                    exit(1)
                else:
                    return labels_dict["labels"]

    def start(self, ds, **kwargs):
        print("Split-Labels started..")

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folders = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

        print("Found {} batches".format(len(batch_folders)))

        for batch_element_dir in batch_folders:
            input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            output_dir = os.path.join(batch_element_dir, self.operator_out_dir)

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

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
                 labels_json="seg_info.json",
                 *args,**kwargs):

        self.labels_json = labels_json

        super().__init__(
            dag,
            name="split-labels",
            python_callable=self.start,
            *args, **kwargs
        )
