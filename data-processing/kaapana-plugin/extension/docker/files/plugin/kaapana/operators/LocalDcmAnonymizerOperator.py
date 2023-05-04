import subprocess
import os
import errno
import glob
import json
import shutil

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalDcmAnonymizerOperator(KaapanaPythonBaseOperator):
    def start(self, ds, **kwargs):
        print("Starting module LocalDcmAnonymizerOperator...")
        print(kwargs)

        if os.environ.get("DCMDICTPATH") is None:
            print("DCMDICTPATH not found...")
            raise ValueError("ERROR")

        anonymize_dict_path = (
            os.path.dirname(os.path.realpath(__file__)) + "/anonymize-tags.json"
        )

        with open(anonymize_dict_path) as data_file:
            anonymize_tags = json.load(data_file)
            if "source" in anonymize_tags:
                del anonymize_tags["source"]

        print("Anonymize tag loaded...")

        erase_tags = ""
        for tag in list(anonymize_tags.keys()):  # [:15]:
            erase_tags += ' --erase-all "(%s)"' % tag

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_dirs = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))]

        print("Found {} batch elements.".format(len(batch_dirs)))

        anon_command = "dcmodify --no-backup --ignore-missing-tags " + erase_tags + " "

        for batch_element_dir in batch_dirs:
            batch_element_out_dir = os.path.join(
                batch_element_dir, self.operator_out_dir
            )
            dcm_files = sorted(
                glob.glob(
                    os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"),
                    recursive=True,
                )
            )
            for dcm_file in dcm_files:
                output_filepath = os.path.join(
                    batch_element_out_dir, os.path.basename(dcm_file)
                )
                if not os.path.exists(os.path.dirname(output_filepath)):
                    os.makedirs(os.path.dirname(output_filepath))

                if not os.path.isfile(output_filepath) or self.overwrite:
                    shutil.copyfile(dcm_file, output_filepath)

                file_command = anon_command + output_filepath
                ret = subprocess.call([file_command], shell=True)
                if ret != 0:
                    print("Something went wrong with dcmodify...")
                    raise ValueError("ERROR")

                if self.single_slice:
                    break

    def __init__(self, dag, bulk=False, overwrite=True, single_slice=False, **kwargs):
        self.dcmodify_path = "dcmodify"
        self.bulk = bulk
        self.overwrite = overwrite
        self.single_slice = single_slice

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

        super().__init__(
            dag=dag, name="dcm-anonymizer", python_callable=self.start, **kwargs
        )
