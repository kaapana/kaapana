import os
import glob
import json
import datetime
from pathlib import Path
import nibabel as nib
import numpy as np
from os.path import basename
import SimpleITK as sitk

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperCaching import cache_operator_output


class LocalExtractSegMetadataOperator(KaapanaPythonBaseOperator):
    """
    Iterates over a bunch of NIFTI images as input.
    Extracts per NIFTI image (w/ 1 class each) the number of voxels per class.
    If a JSON file in json_operator's directory, then just augment information in that JSON file with the gathered voxels per class information.
    If no JSON file in json_operator's directory, the create a JSON file with the gathered voxels per class information.

    **Inputs:**

        * input_operator: Operator which provides the NIFTI SEG images.
        * json_operator: Operator which has already extracted some further metadata and provides that in a JSON file.

    **Outputs**

        * A single json file per batch which contains voxels per class information.

    """

    @cache_operator_output
    def start(self, ds, **kwargs):
        print("Starting module LocalExtractSegMetadataOperator...")
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
                # check if modality is SEG
                if json_data["00000000 CuratedModality_keyword"] in ["SEG"]:
                    print("Valid SEG sample!")
                else:
                    print("Sample is not a SEG --> continue w/ next sample")
                    continue
            else:
                json_data = {}

            # load batch-element's SEG nifti image form input_operator's dir
            batch_element_in_dir = os.path.join(batch_element_dir, self.input_operator)
            seg_nifti_fnames = glob.glob(
                os.path.join(batch_element_in_dir, "*.nii.gz"), recursive=True
            )
            # load batch-element's CT/MR nifti image form input_operator's dir
            batch_element_img_in_dir = os.path.join(
                batch_element_dir, self.img_operator
            )
            img_nifti_fnames = glob.glob(
                os.path.join(batch_element_img_in_dir, "*.nii.gz"), recursive=True
            )
            img_nifti = nib.load(img_nifti_fnames[0])
            # compute volume of 1 voxel in mm³
            spacing = img_nifti.header.get_zooms()
            vox_vol = spacing[0] * spacing[1] * spacing[2]

            label_volume_info = {}
            cca_info = {}
            for seg_nifti_fname in seg_nifti_fnames:
                print(f"{seg_nifti_fname=}")

                # get pixel data from SEG
                seg_pixel_data = nib.load(seg_nifti_fname).get_fdata()

                # compute volume per class
                voxels_per_class = np.count_nonzero(seg_pixel_data)
                vol_per_class = voxels_per_class * vox_vol
                label_volume_info[basename(seg_nifti_fname)] = {
                    "voxels_per_class": f"{voxels_per_class}",
                    "voxel_volume": f"{vox_vol}",
                    "volume_per_class": f"{vol_per_class}",
                }

                # Convert the numpy array to a SimpleITK image
                sitk_image = sitk.GetImageFromArray(seg_pixel_data)
                # Convert the pixel type to 8-bit unsigned integer
                sitk_image = sitk.Cast(sitk_image, sitk.sitkUInt8)
                # Perform connected component analysis
                connected_components = sitk.ConnectedComponent(sitk_image)
                # Use LabelShapeStatisticsImageFilter to get the number of connected components
                label_stats = sitk.LabelShapeStatisticsImageFilter()
                label_stats.Execute(connected_components)
                # Get the number of connected components
                num_components = label_stats.GetNumberOfLabels()
                print("Number of connected components:", num_components)
                cca_info[basename(seg_nifti_fname)] = {}
                for label in range(1, num_components + 1):
                    cca_info[basename(seg_nifti_fname)][
                        label
                    ] = label_stats.GetNumberOfPixels(label)

            print(f"{label_volume_info=}")
            print(f"{cca_info=}")
            json_data.update({"volume_per_class": label_volume_info})
            json_data.update({"connected_component_analysis": cca_info})
            print(f"{json_data=}")

            # save to out_dir
            with open(
                os.path.join(batch_element_out_dir, "metadata_n_segdata.json"),
                "w",
                encoding="utf-8",
            ) as fp:
                json.dump(json_data, fp, indent=4, sort_keys=False, ensure_ascii=False)

    def __init__(
        self,
        dag,
        name="seg-data-characteristics",
        input_operator=None,
        json_operator=None,
        img_operator=None,
        **kwargs,
    ):
        self.input_operator = input_operator.name
        self.json_operator = json_operator.name
        self.img_operator = img_operator.name

        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
