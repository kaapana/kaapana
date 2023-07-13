from pathlib import Path
import subprocess
import os
import json
import shutil
import pydicom
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalDcmAnonymizerOperator(KaapanaPythonBaseOperator):
    """
    Operator to anonymize  sensitive information.

    **Inputs:**

    * Input data which should be anonymized is given via input parameter: input_operator

    **Outputs:**

    * Dicom file: Anonymized .dcm file(s)
    """

    def start(self, ds, **kwargs):
        print("Starting module LocalDcmAnonymizerOperator...")
        print(kwargs)

        if os.environ.get("DCMDICTPATH") is None:
            print("DCMDICTPATH not found...")
            raise ValueError("ERROR")

        erase_tags = ""
        for tag in list(self.anonymize_tags.keys()):  # [:15]:
            erase_tags += ' --erase-all "(%s)"' % tag

        run_dir = Path(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_dirs = list((run_dir / self.batch_name).glob("*"))

        print(f"Found {len(batch_dirs)} batch elements.")

        anon_command = "dcmodify --no-backup --ignore-missing-tags " + erase_tags + " "

        for batch_element_dir in batch_dirs:
            batch_element_out_dir = batch_element_dir / self.operator_out_dir

            dcm_files = sorted(
                [
                    p
                    for p in (batch_element_dir / self.operator_in_dir).rglob("*")
                    if p.is_file() and pydicom.misc.is_dicom(p)
                ]
            )

            print(f"Found {len(dcm_files)} in {batch_element_dir}")

            for dcm_file in dcm_files:
                output_filepath = batch_element_out_dir / dcm_file.name

                if not output_filepath.parent.exists():
                    output_filepath.parent.mkdir(parents=True)

                if not output_filepath.is_file() or self.overwrite:
                    shutil.copyfile(dcm_file, output_filepath)

                file_command = anon_command + str(output_filepath)
                ret = subprocess.call([file_command], shell=True)
                if ret != 0:
                    print("Something went wrong with dcmodify...")
                    raise ValueError("ERROR")

                if self.single_slice:
                    break

    def __init__(
        self,
        dag,
        name="dcm-anonymizer",
        bulk=False,
        overwrite=True,
        single_slice=False,
        anonymize_tags=None,
        **kwargs,
    ):
        """
        :param bulk: process all files of a series or only the first one (default: False).
        :param overwrite: should overwrite or not (default: True).
        :param single_slice: only single slice to be processed or not (default: False).
        :param anonymize_tags: tags to be anonymized (default: None).
        """

        self.dcmodify_path = "dcmodify"
        self.bulk = bulk
        self.overwrite = overwrite
        self.single_slice = single_slice
        self.anonymize_tags = anonymize_tags

        if "DCMDICTPATH" in os.environ and "DICT_PATH" in os.environ:
            # DCMDICTPATH is used by dcmtk / dcmodify
            self.dict_path = os.getenv("DICT_PATH")
        else:
            print("++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("DCMDICTPATH or DICT_PATH ENV NOT FOUND!")
            print("dcmdictpath: {}".format(os.getenv("DCMDICTPATH")))
            print("dict_path: {}".format(os.getenv("DICT_PATH")))
            print("++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            raise ValueError("ERROR")

        if not self.anonymize_tags:
            anonymize_dict_path = (
                os.path.dirname(os.path.realpath(__file__)) + "/anonymize-tags.json"
            )

            with open(anonymize_dict_path) as data_file:
                self.anonymize_tags = json.load(data_file)
                if "source" in self.anonymize_tags:
                    del self.anonymize_tags["source"]

            print("Anonymize tag loaded...")

        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
