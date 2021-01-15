import os
import json
import glob
import pydicom
from datetime import timedelta
from dicomweb_client.api import DICOMwebClient
from multiprocessing.pool import ThreadPool
from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR, INITIAL_INPUT_DIR


class LocalGetRefSeriesOperator(KaapanaPythonBaseOperator):
    def download_series(self, series):
        print("Downloading series: {}".format(series["reference_series_uid"]))
        try:
            download_successful = HelperDcmWeb.downloadSeries(studyUID=series["reference_study_uid"], seriesUID=series["reference_series_uid"], target_dir=series['target_dir'])
            if not download_successful:
                print("Could not download DICOM data!")
                exit(1)

            message = f"OK: Series {series['reference_series_uid']}"
        except Exception as e:
            print("### Something went wrong!")
            print("series: {}".format(series["reference_series_uid"]))
            print(e)
            message = f"ERROR: Series {series['reference_series_uid']}"

        return message

    def get_files(self, ds, **kwargs):
        print("Starting module LocalGetRefSeriesOperator")

        if self.search_policy != 'reference_uid' and self.modality is None:
            print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("")
            print("Parameter 'modality' has to be set for search_policy: {} !".format(self.search_policy))
            print("Abort.")
            print("")
            print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            exit(1)

        client = DICOMwebClient(url=self.pacs_dcmweb, qido_url_prefix="rs", wado_url_prefix="rs", stow_url_prefix="rs")

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]
        download_series_list = []

        for batch_element_dir in batch_folder:
            dcm_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"), recursive=True))
            if len(dcm_files) > 0:
                incoming_dcm = pydicom.dcmread(dcm_files[0])

                if self.search_policy == 'reference_uid':
                    if (0x0008, 0x1115) in incoming_dcm:
                        for ref_series in incoming_dcm[0x0008, 0x1115]:
                            if (0x0020, 0x000E) not in ref_series:
                                print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                                print("")
                                print("Could not extract SeriesUID from referenced DICOM series.")
                                print("Abort.")
                                print("")
                                print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                                exit(1)
                            reference_series_uid = ref_series[0x0020, 0x000E].value
                            pacs_series = client.search_for_series(search_filters={'0020000E': reference_series_uid})
                            print(f"Found series: {len(pacs_series)} for reference_series_uid: {reference_series_uid}")
                            if len(pacs_series) != 1:
                                print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                                print("")
                                print(f"Could not find referenced SeriesUID in the PACS: {reference_series_uid} !")
                                print("Abort.")
                                print("")
                                print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                                exit(1)
                            download_series_list.append(
                                {
                                    "reference_study_uid": pacs_series[0]['0020000D']['Value'][0],
                                    "reference_series_uid": reference_series_uid,
                                    "target_dir": os.path.join(batch_element_dir, self.operator_out_dir)
                                }
                            )
                    else:
                        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        print("")
                        print("Could not find referenced dcm-series within the metadata!")
                        print("Abort.")
                        print("")
                        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        exit(1)
                if self.search_policy == 'study_uid':
                    pacs_series = client.search_for_series(search_filters={'0020000D': incoming_dcm.StudyInstanceUID, '00080060': self.modality.upper()})
                    print(f"Found series: {len(pacs_series)} for modality {self.modality.upper()} in study: {incoming_dcm.StudyInstanceUID}")
                    if len(pacs_series) == 0 or (self.expected_file_count != "all" and len(pacs_series) != self.expected_file_count):
                        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        print("")
                        print(f"Could not identify the searched modality: {self.modality} from the studyUID: {incoming_dcm.StudyInstanceUID} !")
                        print(f"Expected {self.expected_file_count} series of modality {self.modality} - found {len(pacs_series)} series")
                        print("Abort.")
                        print("")
                        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        exit(1)
                    for series in pacs_series:
                        download_series_list.append(
                            {
                                "reference_study_uid": series['0020000D']['Value'][0],
                                "reference_series_uid": series['0020000E']['Value'][0],
                                "target_dir": os.path.join(batch_element_dir, self.operator_out_dir)
                            }
                        )

                if self.search_policy == 'patient_uid':
                    if not (0x0010, 0x0020) in incoming_dcm:
                        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        print("")
                        print("Could not extract PatientUID from referenced DICOM series.")
                        print("Abort.")
                        print("")
                        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        exit(1)

                    patient_uid = incoming_dcm[0x0010, 0x0020].value
                    pacs_series = client.search_for_series(search_filters={'00100020': patient_uid, '00080060': self.modality.upper()})
                    print(f"Found series: {len(pacs_series)} for modality {self.modality.upper()} in patient_uid: {patient_uid}")
                    if len(pacs_series) == 0 or (self.expected_file_count != "all" and len(pacs_series) != self.expected_file_count):
                        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        print("")
                        print(f"Could not identify the searched modality: {self.modality} from the studyUID: {incoming_dcm.StudyInstanceUID} !")
                        print(f"Expected {self.expected_file_count} series of modality {self.modality} - found {len(pacs_series)} series")
                        print("Abort.")
                        print("")
                        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        exit(1)
                    for series in pacs_series:
                        download_series_list.append(
                            {
                                "reference_study_uid": series['0020000D']['Value'][0],
                                "reference_series_uid": series['0020000E']['Value'][0],
                                "target_dir": os.path.join(batch_element_dir, self.operator_out_dir)
                            }
                        )

        if len(download_series_list) == 0:
            print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("")
            print("No series to download could be found!")
            print("Abort.")
            print("")
            print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            exit(1)

        results = ThreadPool(self.parallel_downloads).imap_unordered(self.download_series, download_series_list)

        for result in results:
            print(result)

    def __init__(self,
                 dag,
                 name='get-ref-series',
                 search_policy="reference_uid",  # reference_uid, study_uid, patient_uid
                 modality=None,
                 expected_file_count=1,
                 parallel_downloads=3,
                 pacs_dcmweb_host='http://dcm4chee-service.store.svc',
                 pacs_dcmweb_port='8080',
                 aetitle="KAAPANA",
                 *args, **kwargs):

        self.modality = modality
        self.expected_file_count = expected_file_count
        self.search_policy = search_policy
        self.pacs_dcmweb = pacs_dcmweb_host+":"+pacs_dcmweb_port + "/dcm4chee-arc/aets/"+aetitle.upper()
        self.parallel_downloads = parallel_downloads

        super().__init__(
            dag,
            name=name,
            python_callable=self.get_files,
            execution_timeout=timedelta(minutes=60),
            *args, **kwargs
        )
