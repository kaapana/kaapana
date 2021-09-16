import os
import json
import glob
import pydicom
from os.path import join, basename, dirname
from datetime import timedelta
from dicomweb_client.api import DICOMwebClient
from multiprocessing.pool import ThreadPool
from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalGetRefSeriesOperator(KaapanaPythonBaseOperator):
    def download_series(self, series):
        print("# Downloading series: {}".format(series["reference_series_uid"]))
        try:
            download_successful = HelperDcmWeb.downloadSeries(
                seriesUID=series["reference_series_uid"],
                target_dir=series['target_dir']
            )
            if not download_successful:
                exit(1)
            message = f"OK: Series {series['reference_series_uid']}"
        except Exception as e:
            print(f"#### Something went wrong: {series['reference_series_uid']}")
            print(e)
            message = f"ERROR: Series {series['reference_series_uid']}"

        return message

    def get_files(self, ds, **kwargs):
        print("# Starting module LocalGetRefSeriesOperator")

        client = DICOMwebClient(url=self.pacs_dcmweb, qido_url_prefix="rs", wado_url_prefix="rs", stow_url_prefix="rs")

        run_dir = join(self.workflow_dir, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(join(run_dir, self.batch_name, '*'))]
        download_series_list = []

        print("#")
        print(f"# Modality:       {self.modality}")
        print(f"# Target_level:   {self.target_level}")
        print(f"# Search_policy:  {self.search_policy}")
        print(f"# Expected_count: {self.expected_file_count}")
        print("#")

        if self.target_level == "batch" and self.search_policy == None:
            target_dir = join(run_dir, self.operator_out_dir)
            print("#")
            print(f"# Target:     batch-level")
            print(f"# target_dir: {target_dir}")
            print("#")
            search_filters = {}
            for dicom_tag in self.dicom_tags:
                search_filters[dicom_tag["id"]] = dicom_tag["value"]
            print("#")
            print("# Searching for series with the following filters:")
            print(json.dumps(search_filters, indent=4, sort_keys=True))
            print("#")
            pacs_series = client.search_for_series(search_filters=search_filters)
            print(f"Found series: {len(pacs_series)}")
            if len(pacs_series) == 0 or (self.expected_file_count != "all" and len(pacs_series) != self.expected_file_count):
                print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("# ")
                print(f"Found images != expected file_count.")
                print(f"Expected {self.expected_file_count} series - found {len(pacs_series)} series")
                print("# Abort.")
                print("# ")
                print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                exit(1)
            for series in pacs_series:
                series_uid = series['0020000E']['Value'][0]
                download_series_list.append(
                    {
                        "reference_series_uid": series_uid,
                        "target_dir": join(target_dir, series_uid, self.operator_out_dir)
                    }
                )

            target_dir = join(run_dir, self.operator_out_dir)
            print("#")
            print(f"# Target:     batch-level")
            print(f"# target_dir: {target_dir}")
            print("#")
            search_filters = {}
            for dicom_tag in self.dicom_tags:
                search_filters[dicom_tag["id"]] = dicom_tag["value"]
            print("#")
            print("# Searching for series with the following filters:")
            print(json.dumps(search_filters, indent=4, sort_keys=True))
            print("#")
            pacs_series = client.search_for_series(search_filters=search_filters)
            print(f"Found series: {len(pacs_series)}")
            if len(pacs_series) == 0 or (self.expected_file_count != "all" and len(pacs_series) != self.expected_file_count):
                print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("# ")
                print(f"Found images != expected file_count.")
                print(f"Expected {self.expected_file_count} series - found {len(pacs_series)} series")
                print("# Abort.")
                print("# ")
                print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                exit(1)
            for series in pacs_series:
                series_uid = series['0020000E']['Value'][0]
                download_series_list.append(
                    {
                        "reference_series_uid": series_uid,
                        "target_dir": join(target_dir, series_uid, self.operator_out_dir)
                    }
                )

        elif self.target_level == "batch_element":
            for batch_element_dir in batch_folder:
                print("#")
                print(f"# processing:        {batch_element_dir}")
                search_filters = {}
                for dicom_tag in self.dicom_tags:
                    search_filters[dicom_tag["id"]] = dicom_tag["value"]

                if self.search_policy == 'reference_uid' or self.search_policy == 'study_uid' or self.search_policy == 'patient_uid':
                    dcm_files = sorted(glob.glob(join(batch_element_dir, self.operator_in_dir, "*.dcm*"), recursive=True))
                    if len(dcm_files) > 0:
                        incoming_dcm = pydicom.dcmread(dcm_files[0])
                    else:
                        print(f"# Could not find any input DICOM series -> search_policy: {self.search_policy}")
                        exit(1)

                if self.search_policy == None:
                    print("No search_policy -> only dicom_tags will be used...")

                elif self.search_policy == 'reference_uid':
                    ref_series_items = None
                    if (0x0008, 0x1115) in incoming_dcm:
                        ref_series_items = incoming_dcm[0x0008, 0x1115].value
                    if (0x3006,0x0010) in incoming_dcm and (0x3006,0x0012) in incoming_dcm[0x3006,0x0010].value[0] and (0x3006,0x0014) in incoming_dcm[0x3006,0x0010].value[0][0x3006,0x0012].value[0]:
                        ref_series_items = incoming_dcm[0x3006,0x0010].value[0][0x3006,0x0012].value[0][0x3006,0x0014].value
                    if ref_series_items is not None:
                        for ref_series in ref_series_items:
                            if (0x0020, 0x000E) not in ref_series:
                                print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                                print("# ")
                                print("# Could not extract SeriesUID from referenced DICOM series.")
                                print("# Abort.")
                                print("# ")
                                print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                                exit(1)
                            search_filters['SeriesInstanceUID'] = str(ref_series[0x0020, 0x000E].value)
                            break
                    else:
                        print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        print("# ")
                        print("# Could not find referenced dcm-series within the metadata!")
                        print("# Abort.")
                        print("# ")
                        print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        exit(1)
                elif self.search_policy == 'study_uid':
                    search_filters['StudyInstanceUID'] = incoming_dcm.StudyInstanceUID
                    if self.modality:
                        search_filters['Modality'] = self.modality.upper()

                elif self.search_policy == 'patient_uid':
                    if not (0x0010, 0x0020) in incoming_dcm:
                        print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        print("# ")
                        print("# Could not extract PatientUID from referenced DICOM series.")
                        print("# Abort.")
                        print("# ")
                        print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        exit(1)

                    patient_uid = incoming_dcm[0x0010, 0x0020].value
                    search_filters['PatientID'] = patient_uid
                    if self.modality:
                        search_filters['Modality'] = self.modality.upper()

                else:
                    print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                    print("# ")
                    print(f"# Search policy: {self.search_policy} not supported!")
                    print("# Abort.")
                    print("# ")
                    print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                    exit(1)

                pacs_series = client.search_for_series(search_filters=search_filters)
                print(f"Found series: {len(pacs_series)}")
                if len(pacs_series) == 0 or (self.expected_file_count != "all" and len(pacs_series) != self.expected_file_count):
                    print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                    print("# ")
                    print(f"Found images != expected file_count.")
                    print(f"Expected {self.expected_file_count} series - found {len(pacs_series)} series")
                    print("#")
                    print("# Filters used:")
                    print(json.dumps(search_filters, indent=4, sort_keys=True))
                    print("#")
                    print("# Abort.")
                    print("# ")
                    print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                    exit(1)
                for series in pacs_series:
                    series_uid = series['0020000E']['Value'][0]

                    if self.target_level == "batch":
                        target_dir = join(run_dir, self.operator_out_dir, series_uid, self.operator_out_dir)
                    else:
                        target_dir = join(batch_element_dir, self.operator_out_dir)

                    download_series_list.append(
                        {
                            "reference_series_uid": series_uid,
                            "target_dir": target_dir,
                        }
                    )
        else:
            print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("# ")
            print(f"# search_policy: {self.search_policy}")
            print("# AND")
            print(f"# target_level:  {self.target_level}")
            print("# ")
            print("# ---> NOT SUPPORTED!")
            print("# ")
            print("# Abort.")
            print("# ")
            print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            exit(1)

        if len(download_series_list) == 0:
            print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("# ")
            print("# No series to download could be found!")
            print("# Abort.")
            print("# ")
            print("# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            exit(1)

        if self.limit_file_count != None:
            download_series_list = download_series_list[:self.limit_file_count]

        results = ThreadPool(self.parallel_downloads).imap_unordered(self.download_series, download_series_list)

        for result in results:
            print(result)
            if "error" in result.lower():
                exit(1)

    def __init__(self,
                 dag,
                 name='get-ref-series',
                 search_policy="reference_uid",  # reference_uid, study_uid, patient_uid
                 modality=None,
                 target_level="batch_element",
                 dicom_tags=[],
                 expected_file_count=1,  # int or 'all'
                 limit_file_count=None,
                 parallel_downloads=3,
                 pacs_dcmweb_host='http://dcm4chee-service.store.svc',
                 pacs_dcmweb_port='8080',
                 aetitle="KAAPANA",
                 batch_name=None,
                 *args, **kwargs):

        self.modality = modality
        self.target_level = target_level
        self.dicom_tags = dicom_tags  # studyID dicom_tags=[{'id':'StudyID','value':'nnUnet'},{...}]
        self.expected_file_count = expected_file_count
        self.limit_file_count = limit_file_count
        self.search_policy = search_policy
        self.pacs_dcmweb = pacs_dcmweb_host+":"+pacs_dcmweb_port + "/dcm4chee-arc/aets/"+aetitle.upper()
        self.parallel_downloads = parallel_downloads
        self.batch_name = batch_name

        super().__init__(
            dag,
            name=name,
            batch_name=batch_name,
            python_callable=self.get_files,
            execution_timeout=timedelta(minutes=120),
            *args, **kwargs
        )
