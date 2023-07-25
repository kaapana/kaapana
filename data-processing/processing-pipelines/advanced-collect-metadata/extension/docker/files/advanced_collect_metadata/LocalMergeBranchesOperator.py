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
from kaapana.operators.HelperFederated import federated_sharing_decorator


class LocalMergeBranchesOperator(KaapanaPythonBaseOperator):
    """
    Operator to merge results of 2 operators coming from 2 different branches together.
    This is done by just copying the results of the 2 previous operators in 1 directory.

    **Inputs:**

        * first_input_operator: First operator of which results should be merged.
        * second_input_operator: Second operator of which results should be merged.
        * level: "batch" or "element" level specifying the level where the out_dirs of the 2 input_operators exist.

    **Outputs**

        * Merged/combined result files of input_operators' out_dir in out_dir of this operator.

    """

    @cache_operator_output
    @federated_sharing_decorator
    def start(self, ds, **kwargs):
        print("Starting module LocalMergeBranchesOperator...")
        print(kwargs)

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        if self.level == "element":
            dirs = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))]
        elif self.level == "batch":
            dirs = [run_dir]

        for dir_ in dirs:
            # create out_dir on given level
            out_dir_ = os.path.join(dir_, self.operator_out_dir)
            Path(out_dir_).mkdir(exist_ok=True)

            first_in_dir_ = os.path.join(dir_, self.first_input_operator)
            frist_fnames = glob.glob(os.path.join(first_in_dir_, "*"), recursive=True)
            print(f"{frist_fnames=}")
            second_in_dir_ = os.path.join(dir_, self.second_input_operator)
            second_fnames = glob.glob(os.path.join(second_in_dir_, "*"), recursive=True)
            print(f"{second_fnames=}")
            fnames = frist_fnames + second_fnames

            for idx, fname in enumerate(fnames):
                src = os.path.join(fname)
                dst = os.path.join(out_dir_, f"{idx}-{basename(fname)}")
                print(f"Source: {src}")
                print(f"Destination: {dst}")
                shutil.copy(src, dst)

    def __init__(
        self,
        dag,
        name="merge_branches",
        first_input_operator=None,
        second_input_operator=None,
        level="element",
        **kwargs,
    ):
        self.first_input_operator = first_input_operator.name
        self.second_input_operator = second_input_operator.name
        self.level = level

        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
