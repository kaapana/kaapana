import os
import json
import glob
import pydicom
from dicomweb_client.api import DICOMwebClient
from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalGetRefSeriesOperator(KaapanaPythonBaseOperator):

    def get_files(self, ds, **kwargs):
        print("Starting module LocalGetRefSeriesOperator")

        if self.search_policy != 'reference_uid':
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
            print("batch_element_dir: {}".format(batch_element_dir))
            dcm_files = sorted(glob.glob(os.path.join(batch_element_dir, "initial-input", "*.dcm*"), recursive=True))
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
                            if len(pacs_series) != 1:
                                print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                                print("")
                                print("Could not find referenced SeriesUID in the PACS: {} !".format(reference_series_uid))
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
                    if len(pacs_series) != 1:
                        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        print("")
                        print("Could not identify the searched modality: {} from the studyUID: {} !".format(self.modality, incoming_dcm.StudyInstanceUID))
                        print("Number of possible DICOMs in the PACS: {}".format(len(pacs_series)))
                        print("Abort.")
                        print("")
                        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        exit(1)
                    download_series_list.append(
                        {
                            "reference_study_uid": pacs_series[0]['0020000D']['Value'][0],
                            "reference_series_uid": pacs_series[0]['0020000E']['Value'][0],
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
                    if len(pacs_series) != 1:
                        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        print("")
                        print("Could not identify the searched modality: {} from the PatientUID: {} !".format(self.modality, patient_uid))
                        print("Number of possible DICOMs in the PACS: {}".format(len(pacs_series)))
                        print("Abort.")
                        print("")
                        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        exit(1)
                    download_series_list.append(
                        {
                            "reference_study_uid": pacs_series[0]['0020000D']['Value'][0],
                            "reference_series_uid": pacs_series[0]['0020000E']['Value'][0],
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

        for series in download_series_list:
            print("Downloading series: {}".format(series["reference_series_uid"]))
            HelperDcmWeb.downloadSeries(studyUID=series["reference_study_uid"], seriesUID=series["reference_series_uid"], target_dir=series['target_dir'])


    def __init__(self,
                 dag,
                 search_policy="reference_uid",
                 modality = None,
                 pacs_dcmweb_host='http://dcm4chee-service.store.svc',
                 pacs_dcmweb_port='8080',
                 aetitle="KAAPANA",
                 *args, **kwargs):

        self.modality = modality
        self.search_policy = search_policy
        self.pacs_dcmweb = pacs_dcmweb_host+":"+pacs_dcmweb_port + "/dcm4chee-arc/aets/"+aetitle.upper()

        super().__init__(
            dag,
            name='get-ref-series',
            python_callable=self.get_files,
            *args, **kwargs
        )
