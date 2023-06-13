import os
import glob
import json
import datetime
from pathlib import Path
import nibabel as nib
import numpy as np

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperCaching import cache_operator_output


class LocalExtractImgIntensitiesOperator(KaapanaPythonBaseOperator):
    """
    Takes NIFTI image as input.
    Extracts intensity values and their appearance frequence aka information to compute an intensity histogram from the NIFTI image's pixel data.
    If a JSON file in json_operator's directory, then just augment information in that JSON file with the gathered histogram information.
    If no JSON file in json_operator's directory, the create a JSON file with the gathered histogram information.

    **Inputs:**

        * input_operator: Operator which provides the NIFTI images from which intensity values are read and extracted.
        * json_operator: Operator which has already extracted some further metadata and provides that in a JSON file.

    **Outputs**

        * A single json file per input NIFTI image which contains intensity histogram information.

    """

    @cache_operator_output
    def start(self, ds, **kwargs):
        print("Starting module LocalExtractImgIntensitiesOperator...")
        print(kwargs)

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_dirs = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))]

        for batch_element_dir in batch_dirs:
            # create batch-element out dir
            batch_element_out_dir = os.path.join(
                batch_element_dir, self.operator_out_dir
            )
            Path(batch_element_out_dir).mkdir(exist_ok=True)

            # check if json_operator is defined; if yes load existing json file from json_operator's dir
            if self.json_operator:
                batch_element_json_in_dir = os.path.join(
                    batch_element_dir, self.json_operator
                )
                json_fname = glob.glob(
                    os.path.join(batch_element_json_in_dir, "*.json"), recursive=True
                )[0]
                # load json file
                f = open(json_fname)
                json_data = json.load(f)
                # check if modality in CT or MR
                if json_data["00000000 CuratedModality_keyword"] not in ["CT", "MR"]:
                    print("sample is not a CT or MR image --> continue w/ next sample")
                    continue
            else:
                json_data = {}

            # load batch-element's nifti image form input_operator's dir
            batch_element_in_dir = os.path.join(batch_element_dir, self.input_operator)
            nifti_fname = glob.glob(
                os.path.join(batch_element_in_dir, "*.nii.gz"), recursive=True
            )[0]
            nifti = nib.load(nifti_fname)

            pixel_data = nifti.get_fdata()
            unique_values, counts = np.unique(pixel_data, return_counts=True)
            histo_dict = {
                f"{value}": f"{count}" for value, count in zip(unique_values, counts)
            }
            json_data["pixel_intensities_n_freq"] = histo_dict

            # save to out_dir
            with open(
                os.path.join(batch_element_out_dir, "metadata_n_histodata.json"),
                "w",
                encoding="utf-8",
            ) as fp:
                json.dump(json_data, fp, indent=4, sort_keys=False, ensure_ascii=False)

    def __init__(
        self,
        dag,
        name="extract-img-intensities",
        input_operator=None,
        json_operator=None,
        **kwargs,
    ):
        self.input_operator = input_operator.name
        self.json_operator = json_operator.name

        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)