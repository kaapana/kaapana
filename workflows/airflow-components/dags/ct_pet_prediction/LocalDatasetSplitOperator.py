#!/bin/python3
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from datetime import timedelta
import uuid
import os
import glob
import shutil
from pathlib import Path
import random

class LocalDatasetSplitOperator(KaapanaPythonBaseOperator):

    def move_data(self, series_list, dir_name):
        datset_dir = os.path.join(os.path.dirname(self.batches_input_dir), self.operator_out_dir, dir_name)
        for series in series_list:
            print()
            print("Moving series data: {}".format(os.path.basename(series)))

            files_grabbed = []
            for extension in self.file_extensions:
                files_grabbed.extend(glob.glob(os.path.join(series, "**", extension), recursive=True))

            print("Found {} files to move.".format(len(files_grabbed)))

            for file_grabbed in files_grabbed:
                print("Moving: {}".format(file_grabbed))
                target_path = os.path.join(datset_dir, os.path.basename(series))
                if self.keep_dir_structure:
                    target_path = os.path.join(target_path, file_grabbed.replace(os.path.join(series, self.input_dir)+"/", ""))
                else:
                    target_path = os.path.join(target_path, os.path.basename(file_grabbed))

                Path(os.path.dirname(target_path)).mkdir(parents=True, exist_ok=True)
                if self.copy_target_data:
                    shutil.copy2(file_grabbed, target_path)
                else:
                    shutil.move(file_grabbed, target_path)
            print("done")

    def start(self, ds, **kwargs):
        self.run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        self.batches_input_dir = os.path.join(self.run_dir, BATCH_NAME)
        self.input_dir = os.path.join(self.run_dir, self.operator_in_dir)

        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("Starting DatsetSplitOperator:")
        print()
        print("batches_input_dir: {}".format(self.batches_input_dir))
        print("input_dir: {}".format(self.input_dir))
        print("operator_out_dir: {}".format(self.operator_out_dir))
        print("file_extensions: {}".format(self.file_extensions))
        print("keep_dir_structure: {}".format(self.keep_dir_structure))
        print("copy_target_data: {}".format(self.copy_target_data))
        print("train_percentage: {}".format(self.train_percentage))
        print("test_percentage: {}".format(self.test_percentage))
        print("validation_percentage: {}".format(self.validation_percentage))
        print("shuffle_seed: {}".format(self.shuffle_seed))
        print()

        self.file_extensions = self.file_extensions.split(",")
        self.shuffle_seed = random.randint(0, 50) if self.shuffle_seed == None else self.shuffle_seed

        if (self.test_percentage + self.train_percentage + self.validation_percentage) != 100:
            print("Please specify reasonable percentages (sum == 100%)")
            print("train_percentage: {}".format(self.train_percentage))
            print("test_percentage: {}".format(self.test_percentage))
            print("validation_percentage: {}".format(self.validation_percentage))
            exit(1)

        series_list = [f.path for f in os.scandir(self.batches_input_dir) if f.is_dir()]
        series_list.sort()

        series_count = len(series_list)
        print("Found {} series.".format(series_count))

        train_count = round((series_count/100)*self.train_percentage)
        validation_count = round((series_count/100)*self.validation_percentage)
        test_count = round((series_count/100)*self.test_percentage)

        rest = series_count - train_count - validation_count - test_count
        train_count += rest

        print()
        print("Train-datset-size: {}".format(train_count))
        print("Test-datset-size: {}".format(test_count))
        print("Validation-datset-size: {}".format(validation_count))
        print()

        if (train_count + validation_count + test_count) != series_count:
            print("Something went wrong! -> dataset-splits != series-count!")
            exit(1)

        print("Using shuffle-seed: {}".format(self.shuffle_seed))
        random.seed(self.shuffle_seed)
        random.shuffle(series_list)
        print()

        train_series = series_list[:train_count]
        validation_series = series_list[train_count:train_count+validation_count]
        test_series = series_list[train_count+validation_count:]

        self.move_data(train_series, "train")
        self.move_data(validation_series, "validation")
        self.move_data(test_series, "test")

    def __init__(self,
                 dag,
                 train_percentage=80,
                 test_percentage=10,
                 validation_percentage=10,
                 shuffle_seed=None,
                 operator_out_dir='datasets',
                 file_extensions='*.npy,*.pkl,*.zip,*.dcm,*.nrrd,*.nii,*.nii.gz',
                 keep_dir_structure=False,
                 copy_target_data=False,
                 *args, **kwargs):

        self.train_percentage = train_percentage
        self.test_percentage = test_percentage
        self.validation_percentage = validation_percentage
        self.shuffle_seed = shuffle_seed
        self.operator_out_dir = operator_out_dir
        self.file_extensions = file_extensions
        self.keep_dir_structure = keep_dir_structure
        self.copy_target_data = copy_target_data

        super(LocalDatasetSplitOperator, self).__init__(
            dag,
            name='dataset-split',
            python_callable=self.start,
            operator_out_dir=self.operator_out_dir,
            *args,
            **kwargs,
        )
