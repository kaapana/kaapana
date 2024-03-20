import os
import glob
import json
import datetime
from pathlib import Path
import nibabel as nib
import pydicom
import numpy as np
from os.path import basename

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

        # create out_dir on batch level
        batch_out_dir = os.path.join(run_dir, self.operator_out_dir)
        Path(batch_out_dir).mkdir(exist_ok=True)

        histo_dict = {}
        concat_json_data = {}
        valid_images = 0
        for batch_element_dir in batch_dirs:
            print(f"CURRENT BATCH ELEMENT: {batch_element_dir=}")

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
                    print("sample is a CT or MR image!")
            else:
                json_data = {}

            # count valid images
            valid_images = valid_images + 1

            ### via DICOM ###
            # load batch-element's nifti image form input_operator's dir
            batch_element_in_dir = os.path.join(batch_element_dir, self.input_operator)
            dcm_fnames = glob.glob(
                os.path.join(batch_element_in_dir, "*.dcm"), recursive=True
            )

            # read slices and stack along depth axis
            slices = [pydicom.dcmread(file).pixel_array for file in dcm_fnames]
            new_slices = []
            for arr in slices:
                new_slices.append(
                    arr
                )  # Note: should work with arr.ndim=3 and arr.ndim=2
            slices = new_slices
            volume = np.stack(slices, axis=-1)

            # rescale pixel values with slope and intersect (same values for all slices of volume)
            ds = pydicom.dcmread(dcm_fnames[0])
            slope = (
                ds.RescaleSlope
                if "RescaleSlope" in ds
                else (
                    ds.SharedFunctionalGroupsSequence[0]
                    .PixelValueTransformationSequence[0]
                    .RescaleSlope
                )
            )  # ds.RescaleSlope; (0028,1053)
            intercept = (
                ds.RescaleIntercept
                if "RescaleIntercept" in ds
                else (
                    ds.SharedFunctionalGroupsSequence[0]
                    .PixelValueTransformationSequence[0]
                    .RescaleIntercept
                )
            )  # ds.RescaleIntercept; 	(0028,1052)
            volume = volume * slope + intercept
            print(f"MIN Value: {np.min(volume)} ; MAX value: {np.max(volume)}")
            if np.max(volume) > 4095:
                print(
                    f"# WARNING: grayscale values of current image exceed HU value range [0; 4095] with a MAXIMUM VALUE = {np.max(volume)}"
                )

            # retrieve grayscale histo values and add to histo_dict
            unique_values, counts = np.unique(volume, return_counts=True)
            histo_dict_el = {
                f"{value}": f"{count}" for value, count in zip(unique_values, counts)
            }
            for key, value in histo_dict_el.items():
                if key not in histo_dict:
                    histo_dict[key] = int(value)
                else:
                    histo_dict[key] = int(histo_dict[key]) + int(value)

            # append metadata to concat_json_data dict
            concat_json_data[basename(batch_element_dir)] = json_data

        # sort histo_dict with increasing grayscale values
        sorted_histo_dict = dict(
            sorted(histo_dict.items(), key=lambda item: float(item[0]))
        )

        # merge concat_json_data and histo_dict dicts
        concat_json_data["histo_values"] = sorted_histo_dict
        # add information of how many images in dataset
        concat_json_data["num_images"] = valid_images

        # save to out_dir
        with open(
            os.path.join(batch_out_dir, "metadata_n_mergedhisto.json"),
            "w",
            encoding="utf-8",
        ) as fp:
            json.dump(
                concat_json_data, fp, indent=4, sort_keys=False, ensure_ascii=False
            )

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
