#!/bin/python3
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from datetime import timedelta
import uuid
import os
import glob
import json
import shutil
from pathlib import Path
import random


class LocalNnUnetPrepOperator(KaapanaPythonBaseOperator):

    def move_file(self, source, target):
        Path(os.path.dirname(target)).mkdir(parents=True, exist_ok=True)
        if self.copy_target_data:
            shutil.copy2(source, target)
        else:
            shutil.move(source, target)

    def start(self, ds, **kwargs):
        self.run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        self.batches_input_dir = os.path.join(self.run_dir, BATCH_NAME)
        self.input_dir = os.path.join(self.run_dir, self.operator_in_dir)
        self.output_dir = os.path.join(self.run_dir, self.operator_out_dir)

        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("Starting DatsetSplitOperator:")
        print()
        print()

        # case_identifier_XXXX.nii.gz
        # Label files are saved as case_identifier.nii.gz
        # nnUNet_raw_data_base/nnUNet_raw_data/Task001_BrainTumour/
        # ├── dataset.json
        # ├── imagesTr
        # │   ├── BRATS_001_0000.nii.gz
        # │   ├── BRATS_001_0001.nii.gz
        # │   ├── BRATS_001_0002.nii.gz
        # │   ├── BRATS_001_0003.nii.gz
        # │   ├── BRATS_002_0000.nii.gz
        # │   ├── BRATS_002_0001.nii.gz
        # │   ├── BRATS_002_0002.nii.gz
        # │   ├── BRATS_002_0003.nii.gz
        # │   ├── ...
        # ├── imagesTs
        # │   ├── BRATS_485_0000.nii.gz
        # │   ├── BRATS_485_0001.nii.gz
        # │   ├── BRATS_485_0002.nii.gz
        # │   ├── BRATS_485_0003.nii.gz
        # │   ├── BRATS_486_0000.nii.gz
        # │   ├── BRATS_486_0001.nii.gz
        # │   ├── BRATS_486_0002.nii.gz
        # │   ├── BRATS_486_0003.nii.gz
        # │   ├── ...
        # └── labelsTr
        #     ├── BRATS_001.nii.gz
        #     ├── BRATS_002.nii.gz
        #     ├── BRATS_003.nii.gz
        #     ├── BRATS_004.nii.gz
        #     ├── ...

        template_dataset_json = {
            "name": self.training_name,
            "description": self.training_description,
            "reference": self.training_reference,
            "licence": self.licence,
            "relase": self.version,
            "tensorImageSize": self.tensor_size,
            "modality": self.modality,
            "labels": self.labels,
            "numTraining": self.training_count,
            "numTest": self.test_count,
            "training": [],
            "test": []
        }

        series_list = [f.path for f in os.scandir(self.batches_input_dir) if f.is_dir()]
        series_list.sort()

        series_count = len(series_list)
        test_count = round((series_count/100)*self.test_percentage)
        train_count = series_count - test_count

        template_dataset_json["numTraining"] = train_count
        template_dataset_json["numTest"] = test_count

        print("")
        print("All series count:  {}".format(series_count))
        print("Train-datset-size: {}".format(train_count))
        print("Test-datset-size:  {}".format(test_count))
        print("")

        if (train_count + test_count) != series_count:
            print("Something went wrong! -> dataset-splits != series-count!")
            exit(1)

        print("Using shuffle-seed: {}".format(self.shuffle_seed))
        random.seed(self.shuffle_seed)
        random.shuffle(series_list)
        print("")

        train_series = series_list[:train_count]
        test_series = series_list[train_count:]

        for series in train_series:
            print("Preparing train series: {}".format(series))
            seg_dir = os.path.join(series, self.seg_input_operator.operator_out_dir)
            dicom_dir = os.path.join(series, self.dicom_input_operator.operator_out_dir)

            seg_nifti = glob.glob(os.path.join(seg_dir, "*.nii.gz"), recursive=True)
            if len(seg_nifti) != 1:
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("")
                print("Error with training seg-file!")
                print("Found {} files at: {}".format(len(seg_nifti), seg_dir))
                print("Expected only one file! -> abort.")
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("")
                exit(1)

            dicom_nifti = glob.glob(os.path.join(dicom_dir, "*.nii.gz"), recursive=True)
            if len(dicom_nifti) != 1:
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("")
                print("Error with training image-file!")
                print("Found {} files at: {}".format(len(dicom_nifti), dicom_dir))
                print("Expected only one file! -> abort.")
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("")
                exit(1)

            target_dicom_path = os.path.join(self.output_dir, "imagesTr", os.path.basename(dicom_nifti[0]).replace(".nii.gz", "_0000.nii.gz"))
            self.move_file(source=dicom_nifti[0], target=target_dicom_path)

            target_seg_path = os.path.join(self.output_dir, "labelsTr", os.path.basename(seg_nifti[0]))
            self.move_file(source=seg_nifti[0], target=target_seg_path)

            template_dataset_json["training"].append(
                {
                    "image": target_dicom_path.replace(self.run_dir,""),
                    "label": target_seg_path.replace(self.run_dir,"")
                }
            )

        for series in test_series:
            print("Preparing test series: {}".format(series))
            seg_dir = os.path.join(series, self.seg_input_operator.operator_out_dir)
            dicom_dir = os.path.join(series, self.dicom_input_operator.operator_out_dir)

            seg_nifti = glob.glob(os.path.join(seg_dir, "*.nii.gz"), recursive=True)
            if len(seg_nifti) != 1:
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("")
                print("Error with test seg-file!")
                print("Found {} files at: {}".format(len(seg_nifti), seg_dir))
                print("Expected only one file! -> abort.")
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("")
                exit(1)

            dicom_nifti = glob.glob(os.path.join(dicom_dir, "*.nii.gz"), recursive=True)
            if len(dicom_nifti) != 1:
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("")
                print("Error with test image-file!")
                print("Found {} files at: {}".format(len(dicom_nifti), dicom_dir))
                print("Expected only one file! -> abort.")
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("")
                exit(1)

            target_dicom_path = os.path.join(self.output_dir, "imagesTs", os.path.basename(dicom_nifti[0]))
            self.move_file(source=dicom_nifti[0], target=target_dicom_path)

            template_dataset_json["test"].append(target_dicom_path.replace(self.run_dir,""))

        with open(os.path.join(self.output_dir, 'dataset.json'), 'w') as fp:
            json.dump(template_dataset_json, fp, indent=4, sort_keys=True)

    def __init__(self,
                 dag,
                 training_name,
                 seg_input_operator,
                 dicom_input_operator,
                 modality={
                     "0": "CT"
                 },
                 labels={
                     "0": "background",
                     "1": "Liver",
                 },
                 licence="NA",
                 version="NA",
                 training_description="nnUnet Segmentation",
                 training_reference="nnUnet",
                 tensor_size="3D",
                 shuffle_seed=None,
                 test_percentage=10,
                 copy_target_data=False,
                 operator_out_dir='datasets',
                 file_extensions='*.nii.gz',
                 *args, **kwargs):

        self.seg_input_operator = seg_input_operator
        self.dicom_input_operator = dicom_input_operator
        self.training_name = training_name
        self.training_description = training_description
        self.training_reference = training_reference
        self.licence = licence
        self.version = version
        self.tensor_size = tensor_size
        self.modality = modality
        self.labels = labels
        self.training_count = None
        self.test_count = None

        self.test_percentage = test_percentage
        self.shuffle_seed = shuffle_seed
        self.operator_out_dir = operator_out_dir
        self.file_extensions = file_extensions
        self.copy_target_data = copy_target_data

        super().__init__(
            dag,
            name='dataset-split',
            python_callable=self.start,
            operator_out_dir=self.operator_out_dir,
            *args,
            **kwargs,
        )
