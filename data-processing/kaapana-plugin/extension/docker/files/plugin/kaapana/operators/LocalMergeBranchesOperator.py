import os
import glob
import json
import datetime
from pathlib import Path
import nibabel as nib
import numpy as np
from os.path import basename
import shutil

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperCaching import cache_operator_output


class LocalMergeBranchesOperator(KaapanaPythonBaseOperator):
    """
    Operator to merge results of 2 operators coming from 2 different branches together.
    This is done by just copying the results of the 2 previous operators in 1 directory.

    **Inputs:**

        * first_input_operator: First operator of which results should be merged.
        * second_input_operator: Second operator of which results should be merged.

    **Outputs**

        * Merged/combined result files of input_operators' out_dir in out_dir of this operator.

    """

    @cache_operator_output
    def start(self, ds, **kwargs):
        print("Starting module LocalMergeBranchesOperator...")
        print(kwargs)

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_dirs = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))]

        for batch_element_dir in batch_dirs:

            # create batch-element out dir
            batch_element_out_dir = os.path.join(batch_element_dir, self.operator_out_dir)
            Path(batch_element_out_dir).mkdir(exist_ok=True)

            first_batch_element_in_dir = os.path.join(batch_element_dir, self.first_input_operator)
            frist_fnames = glob.glob(os.path.join(first_batch_element_in_dir, "*"), recursive=True)
            print(f"{frist_fnames=}")
            second_batch_element_in_dir = os.path.join(batch_element_dir, self.second_input_operator)
            second_fnames = glob.glob(os.path.join(second_batch_element_in_dir, "*"), recursive=True)
            print(f"{second_fnames=}")
            fnames = frist_fnames + second_fnames

            for idx, fname in enumerate(fnames):
                src = os.path.join(fname)
                dst = os.path.join(batch_element_out_dir, f"{idx}-{basename(fname)}")
                print(f"Source: {src}")
                print(f"Destination: {dst}")
                shutil.copy(src, dst)

    def __init__(
        self, 
        dag, 
        name="merge_2branches",
        first_input_operator=None,
        second_input_operator=None,
        **kwargs
        ):

        self.first_input_operator = first_input_operator.name
        self.second_input_operator = second_input_operator.name
        
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
