from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperElasticsearch import HelperElasticsearch
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

import os
import glob
import pydicom
from datetime import timedelta
from shutil import copyfile


class LocalMultiAETitleOperator(KaapanaPythonBaseOperator):

    # CTP stores called AE titel in https://dicom.innolitics.com/ciods/stereometric-relationship/clinical-trial-subject/00120020
    AETITLE_IN_META = "00120020 ClinicalTrialProtocolID_keyword"
    AETITLE_DICOM_TAG = "ClinicalTrialProtocolID"
    AETITLE_SEPERATOR = ";"

    def _add_aetitle(self, src_file, target_file, aetitle_to_append):
        ds = pydicom.dcmread(src_file, force=True)
        exisiting = ds[self.AETITLE_DICOM_TAG].value
        print(f"ClinicalTrialProtocolID of incoming files: {exisiting}")
        print(f"ClinicalTrialProtocolID of already present files: {aetitle_to_append}")
        new_aetitle = self.AETITLE_SEPERATOR.join(aetitle_to_append + [exisiting])
        print(f"Setting ClinicalTrialProtocolID for {src_file} to {new_aetitle}")
        ds[self.AETITLE_DICOM_TAG].value = new_aetitle
        print(f"Value of {self.AETITLE_DICOM_TAG} is {ds[self.AETITLE_DICOM_TAG]}")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        ds.save_as(target_file)
        print(f"Wrote {target_file}")
        ds2 = pydicom.dcmread(target_file, force=True)
        print(f"Value of {self.AETITLE_DICOM_TAG} in target file is {ds2[self.AETITLE_DICOM_TAG]}")

    def _copy_files(self, dcm_file_list, input_dir, output_dir):
        for src_file in dcm_file_list:
            target_file = src_file.replace(input_dir, output_dir)
            print(f"Copy {src_file} into output dir {target_file}")
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            copyfile(src_file, target_file)

    def _check_series(self, input_dir, output_dir):
        dcm_file_list = glob.glob(input_dir + "/*.dcm", recursive=True)
        dcm_file = pydicom.dcmread(dcm_file_list[0],force=True)
        series_uid = dcm_file[0x0020, 0x000E].value
        series_trail_subject = dcm_file[self.AETITLE_DICOM_TAG].value
        print(f"Sending AETITLE is: {series_trail_subject}")
        metadata = HelperElasticsearch.get_series_metadata(series_uid)
        if metadata:
            if series_trail_subject in metadata[self.AETITLE_IN_META]:
                print("Reimporting series")
                self._copy_files(dcm_file_list, input_dir, output_dir)
            else:
                print(f"Adding ClinicalTrialProtocolID to incomming files")
                for src_file in dcm_file_list:
                    target_file = src_file.replace(input_dir, output_dir)
                    aetitle_to_append = metadata[self.AETITLE_IN_META]
                    # older indexes only contain a single string but new format is a list
                    if isinstance(aetitle_to_append, str):
                        aetitle_to_append = [aetitle_to_append]
                    
                    self._add_aetitle(src_file, target_file, aetitle_to_append)
        else:
            print("No metadata found for this series, normal import")
            self._copy_files(dcm_file_list, input_dir, output_dir)

    def check(self, ds, **kwargs):
        self.conf = kwargs['dag_run'].conf
        self.dag_run_id = kwargs['dag_run'].run_id
        self.run_dir = os.path.join(WORKFLOW_DIR, self.dag_run_id)
        batch_folder = [f for f in glob.glob(os.path.join(self.run_dir, BATCH_NAME, '*'))]

        for batch_element_dir in batch_folder:
            input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            output_dir = os.path.join(batch_element_dir, self.operator_out_dir)
            self._check_series(input_dir, output_dir)

    def __init__(self,
                 dag,
                 name="multi-aetitle",
                 *args, **kwargs):

        super(LocalMultiAETitleOperator, self).__init__(
            dag=dag,
            name=name,
            python_callable=self.check,
            execution_timeout=timedelta(minutes=180),
            *args,
            **kwargs)
