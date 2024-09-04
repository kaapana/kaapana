import glob
import json
from datetime import timedelta
from multiprocessing.pool import ThreadPool
from os.path import join
from pathlib import Path

import pydicom
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.HelperDcmWeb import get_dcmweb_helper
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.helper.HelperOpensearch import HelperOpensearch
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperCaching import cache_operator_output


class LocalGetRefSeriesOperator(KaapanaPythonBaseOperator):
    """
    Operator to get DICOM series.

    This operator downloads DICOM series from a given PACS system according to specified search filters.
    The downloading is executed in a structured manner such that the downloaded data is saved to target directories named with the series_uid.
    """

    def __init__(
        self,
        dag,
        name: str = "get-ref-series",
        search_policy: str = "reference_uid",  # reference_uid, study_uid, patient_uid
        data_type: str = "dicom",
        modality: str = None,
        target_level: str = "batch_element",
        dicom_tags: list = [],
        expected_file_count: str = "all",  # int or 'all'
        limit_file_count: int = None,
        parallel_downloads: int = 3,
        batch_name: str = None,
        **kwargs,
    ):
        self.modality = modality
        self.data_type = data_type
        self.target_level = target_level
        self.dicom_tags = (
            dicom_tags  # studyID dicom_tags=[{'id':'StudyID','value':'nnUnet'},{...}]
        )
        self.expected_file_count = expected_file_count
        self.limit_file_count = limit_file_count
        self.search_policy = search_policy

        self.parallel_downloads = parallel_downloads
        self.batch_name = batch_name

        super().__init__(
            dag=dag,
            name=name,
            batch_name=batch_name,
            python_callable=self.get_files,
            execution_timeout=timedelta(minutes=120),
            **kwargs,
        )

    def download_series(self, series):
        print("# Downloading series: {}".format(series["reference_series_uid"]))
        try:
            if self.data_type == "dicom":
                download_successful = self.dcmweb_helper.download_series(
                    study_uid=None,
                    series_uid=series["reference_series_uid"],
                    target_dir=series["target_dir"],
                    expected_object_count=series["expected_object_count"],
                )
                if not download_successful:
                    raise ValueError("ERROR")
                message = f"OK: Series {series['reference_series_uid']}"
            elif self.data_type == "json":
                Path(series["target_dir"]).mkdir(parents=True, exist_ok=True)
                meta_data = HelperOpensearch.get_series_metadata(
                    series_instance_uid=series["reference_series_uid"]
                )
                json_path = join(series["target_dir"], "metadata.json")
                with open(json_path, "w") as fp:
                    json.dump(meta_data, fp, indent=4, sort_keys=True)
                message = f"OK: Series {series['reference_series_uid']}"
            else:
                print("Unknown data-mode!")
                message = f"ERROR: Series {series['reference_series_uid']}"

        except Exception as e:
            print(f"#### Something went wrong: {series['reference_series_uid']}")
            print(e)
            message = f"ERROR: Series {series['reference_series_uid']}"

        return message

    @cache_operator_output
    def get_files(self, ds, **kwargs):
        print("# Starting module LocalGetRefSeriesOperator")
        workflow_form = kwargs["dag_run"].conf["workflow_form"]
        dcmweb_endpoint = workflow_form.get("dcmweb_endpoint")

        self.dcmweb_helper = get_dcmweb_helper(
            dcmweb_endpoint=dcmweb_endpoint,
        )
        if self.dcmweb_helper is None:
            print("HelperDcmWeb couldn't be retrieved. Abort")
            exit(1)

        run_dir = join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = [f for f in glob.glob(join(run_dir, self.batch_name, "*"))]
        download_series_list = []
        object_count = None

        print("#")
        print(f"# Modality:       {self.modality}")
        print(f"# Target_level:   {self.target_level}")
        print(f"# Search_policy:  {self.search_policy}")
        print(f"# Expected_count: {self.expected_file_count}")
        print("#")

        if self.target_level == "batch" and self.search_policy is None:
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

            pacs_series = self.dcmweb_helper.search_for_series(
                search_filters=search_filters
            )

            print(f"Found series: {len(pacs_series)}")
            if len(pacs_series) == 0 or (
                self.expected_file_count != "all"
                and len(pacs_series) != self.expected_file_count
            ):
                print(
                    "# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                )
                print("# ")
                print(f"Found images != expected file_count.")
                print(
                    f"Expected {self.expected_file_count} series - found {len(pacs_series)} series"
                )
                print("# Abort.")
                print("# ")
                print(
                    "# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                )
                raise ValueError("ERROR")
            for series in pacs_series:
                series_uid = series["0020000E"]["Value"][0]
                download_series_list.append(
                    {
                        "reference_series_uid": series_uid,
                        "target_dir": join(
                            target_dir, series_uid, self.operator_out_dir
                        ),
                    }
                )

        elif self.target_level == "batch_element":
            for batch_element_dir in batch_folder:
                print("#")
                print(f"# processing:        {batch_element_dir}")
                search_filters = {}
                for dicom_tag in self.dicom_tags:
                    search_filters[dicom_tag["id"]] = dicom_tag["value"]

                if (
                    self.search_policy == "reference_uid"
                    or self.search_policy == "study_uid"
                    or self.search_policy == "patient_uid"
                ):
                    dcm_files = sorted(
                        glob.glob(
                            join(batch_element_dir, self.operator_in_dir, "*.dcm*"),
                            recursive=True,
                        )
                    )
                    if len(dcm_files) > 0:
                        incoming_dcm = pydicom.dcmread(dcm_files[0])
                    else:
                        print(
                            f"# Could not find any input DICOM series -> search_policy: {self.search_policy}"
                        )
                        raise ValueError("ERROR")

                if self.search_policy == None:
                    print("No search_policy -> only dicom_tags will be used...")

                elif self.search_policy == "reference_uid":
                    pacs_series = []
                    if incoming_dcm.Modality == "RTSTRUCT":
                        assert (0x3006, 0x0010) in incoming_dcm
                        ref_object = (
                            incoming_dcm[0x3006, 0x0010]
                            .value[0][0x3006, 0x0012]
                            .value[0][0x3006, 0x0014]
                            .value[0]
                        )
                        search_filters["SeriesInstanceUID"] = (
                            ref_object.SeriesInstanceUID
                        )
                        object_count = len(list(ref_object[0x3006, 0x0016].value))

                    elif incoming_dcm.Modality == "SEG":
                        assert (0x0008, 0x1115) in incoming_dcm
                        ref_object = incoming_dcm[0x0008, 0x1115].value[0]
                        search_filters["SeriesInstanceUID"] = (
                            ref_object.SeriesInstanceUID
                        )
                        object_count = len(list(ref_object[0x0008, 0x114A].value))
                    else:
                        raise ValueError(
                            f"Unsupported modality: {incoming_dcm.Modality}"
                        )

                elif self.search_policy == "study_uid":
                    search_filters["StudyInstanceUID"] = incoming_dcm.StudyInstanceUID
                    if self.modality:
                        search_filters["Modality"] = self.modality.upper()

                elif self.search_policy == "patient_uid":
                    if not (0x0010, 0x0020) in incoming_dcm:
                        print(
                            "# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                        )
                        print("# ")
                        print(
                            "# Could not extract PatientUID from referenced DICOM series."
                        )
                        print("# Abort.")
                        print("# ")
                        print(
                            "# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                        )
                        raise ValueError("ERROR")

                    patient_uid = incoming_dcm[0x0010, 0x0020].value
                    search_filters["PatientID"] = patient_uid
                    if self.modality:
                        search_filters["Modality"] = self.modality.upper()

                else:
                    print(
                        "# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                    )
                    print("# ")
                    print(f"# Search policy: {self.search_policy} not supported!")
                    print("# Abort.")
                    print("# ")
                    print(
                        "# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                    )
                    raise ValueError("ERROR")

                pacs_series = self.dcmweb_helper.search_for_series(
                    search_filters=search_filters
                )
                print(f"Found series: {len(pacs_series)}")
                if len(pacs_series) == 0 or (
                    self.expected_file_count != "all"
                    and len(pacs_series) != self.expected_file_count
                ):
                    print(
                        "# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                    )
                    print("# ")
                    print(f"Found images != expected file_count.")
                    print(
                        f"Expected {self.expected_file_count} series - found {len(pacs_series)} series"
                    )
                    print("#")
                    print("# Filters used:")
                    print(json.dumps(search_filters, indent=4, sort_keys=True))
                    print("#")
                    print("# Abort.")
                    print("# ")
                    print(
                        "# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                    )
                    raise ValueError("ERROR")

                for series in pacs_series:
                    series_uid = series["0020000E"]["Value"][0]

                    if self.target_level == "batch":
                        target_dir = join(
                            run_dir,
                            self.operator_out_dir,
                            series_uid,
                            self.operator_out_dir,
                        )
                    else:
                        target_dir = join(batch_element_dir, self.operator_out_dir)

                    download_series_list.append(
                        {
                            "reference_series_uid": series_uid,
                            "target_dir": target_dir,
                            "expected_object_count": object_count,
                        }
                    )
        else:
            print(
                "# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
            )
            print("# ")
            print(f"# search_policy: {self.search_policy}")
            print("# AND")
            print(f"# target_level:  {self.target_level}")
            print("# ")
            print("# ---> NOT SUPPORTED!")
            print("# ")
            print("# Abort.")
            print("# ")
            print(
                "# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
            )
            raise ValueError("ERROR")

        if len(download_series_list) == 0:
            print(
                "# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
            )
            print("# ")
            print("# No series to download could be found!")
            print("# Abort.")
            print("# ")
            print(
                "# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
            )
            raise ValueError("ERROR")

        if self.limit_file_count is not None:
            download_series_list = download_series_list[: self.limit_file_count]

        with ThreadPool(self.parallel_downloads) as threadpool:
            results = threadpool.imap_unordered(
                self.download_series, download_series_list
            )

            for result in results:
                print(result)
                if "error" in result.lower():
                    raise ValueError("ERROR")
