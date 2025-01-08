import glob
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import timedelta
from os.path import join
from pathlib import Path

import pydicom
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.HelperDcmWeb import get_dcmweb_helper
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.helper import get_opensearch_client
from kaapanapy.settings import OpensearchSettings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class DownloadSeries:
    series_instance_uid: str
    reference_series_uid: str
    study_instance_uid: str
    target_dir: str


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
        dicom_tags: list = [],  # list of dicom tags to filter the series
        parallel_downloads: int = 3,
        batch_name: str = None,
        **kwargs,
    ):
        if data_type not in ["dicom", "json"]:
            raise ValueError("Unknown data-type!")
        if search_policy not in ["reference_uid", "study_uid", "patient_uid"]:
            raise ValueError("Unknown search policy!")

        if search_policy in ["study_uid", "patient_uid"]:
            raise NotImplementedError(
                "search_policy 'study_uid' and 'patient_uid' are not implemented yet! Please use search_policy 'reference_uid' instead."
            )
        if not dicom_tags == []:
            raise NotImplementedError("dicom_tags is not implemented yet!")

        if data_type == "json":
            self.download_function = self.download_metadata_from_opensearch
        elif data_type == "dicom":
            self.download_function = self.download_series_from_pacs

        self.search_policy = search_policy
        self.data_type = data_type

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

    def download_metadata_from_opensearch(self, series: DownloadSeries):
        """Download metadata of a series from opensearch and store it as a json file into target_dir.

        Args:
            series (DownloadSeries): The series to download encapsulated in a DownloadSeries Dataclass.

        Raises:
            ValueError: If the download failed.
        """
        # Create target directory
        Path(series.target_dir).mkdir(parents=True, exist_ok=True)

        # Get metadata from OpenSearch
        meta_data = self.os_client.get(id=series.reference_series_uid)["_source"]

        # Save metadata to json file
        with open(join(series.target_dir, "metadata.json"), "w") as fp:
            json.dump(meta_data, fp, indent=4, sort_keys=True)

        # Check if target directory is empty
        if len(os.listdir(series.target_dir)) == 0:
            raise ValueError(
                f"Download of series {series.series_instance_uid} failed! Target directory is empty."
            )

    def download_series_from_pacs(self, series: DownloadSeries):
        """Download a series from the PACS system.

        Args:
            series (DownloadSeries): The series to download.
        """
        # Check if series is present in PACS. During upload it can happen that the series is not uploaded yet but the segmentation is already there.
        instances = self.dcmweb_helper.get_instances_of_series(
            study_uid=series.study_instance_uid, series_uid=series.reference_series_uid
        )

        self.dcmweb_helper.download_series(
            study_uid=series.study_instance_uid,
            series_uid=series.reference_series_uid,
            target_dir=series.target_dir,
        )

        # Check if number of instances is equal to number of downloaded files
        if len(instances) != len(os.listdir(series.target_dir)):
            raise ValueError(
                f"Download of series {series.series_instance_uid} failed! Number of instances does not match number of downloaded files."
            )

        logger.info(f"Number of instances in PACS: {len(instances)}")
        logger.info(f"Number of downloaded files: {len(os.listdir(series.target_dir))}")
        logger.info(
            f"Downloaded series {series.reference_series_uid} to {series.target_dir}"
        )

    def prepare_download(
        self, path_to_dicom_slice: str, series_dir: str
    ) -> DownloadSeries:
        """Prepare the download of a series. Means:
        - Load the dicom file and get the series instance uid.
        - Get the reference series uid.
        - Get the study instance uid.
        - Depending on the modality, get the reference series uid.
        - Create the target directory for the download.
        - Return a DownloadSeries object, which contains the information needed for the download.

        Args:
            path_to_dicom_slice (str): The path to the dicom slice.
            series_dir (str): The batch element directory of processed dicom slice.

        Raises:
            ValueError: If the modality is unknown.

        Returns:
            DownloadSeries: Dataclass containing the information needed for the download.
        """

        # Load the dicom file
        ds = pydicom.dcmread(join(path_to_dicom_slice))

        # get series instance uid
        series_instance_uid = ds.SeriesInstanceUID
        # get study instance uid
        study_instance_uid = ds.StudyInstanceUID

        if ds.Modality == "SEG":
            # Get the reference series uid
            reference_series_uid = ds.ReferencedSeriesSequence[0].SeriesInstanceUID
        elif ds.Modality == "RTSTRUCT":
            # Get the reference series uid
            reference_series_uid = (
                ds.ReferencedFrameOfReferenceSequence[0]
                .RTReferencedStudySequence[0]
                .RTReferencedSeriesSequence[0]
                .SeriesInstanceUID
            )
        else:
            raise ValueError("Unknown modality!")

        target_dir = join(series_dir, self.operator_out_dir)
        print(f"Target dir: {target_dir}")

        os.makedirs(target_dir, exist_ok=True)

        return DownloadSeries(
            series_instance_uid=series_instance_uid,
            reference_series_uid=reference_series_uid,
            study_instance_uid=study_instance_uid,
            target_dir=target_dir,
        )

    @cache_operator_output
    def get_files(self, ds, **kwargs):
        """Download series from PACS or Opensearch.

        Args:
            ds (dict): The input dictionary.

        Raises:
            ValueError: If the download failed.
        """
        self.dag_run = kwargs["dag_run"].run_id
        logger.info("Starting module LocalGetRefSeriesOperator")
        self.dcmweb_helper = get_dcmweb_helper()
        self.os_client = get_opensearch_client()
        self.opensearch_index = OpensearchSettings().default_index

        series_dirs = glob.glob(
            join(
                self.airflow_workflow_dir,
                self.dag_run,
                self.batch_name,
                "*",
            )
        )  # e.g. /kaapana/mounted/workflows/data/service-segmentation-thumbnail-240916111826725386/batch
        print(f"Series dirs: {series_dirs}")

        download_series_list = []

        if self.search_policy == "reference_uid":
            # Prepare the download
            with ThreadPoolExecutor(max_workers=self.parallel_downloads) as executor:
                futures = [
                    executor.submit(
                        self.prepare_download,
                        join(
                            series_dir,
                            self.operator_in_dir,
                            os.listdir(join(series_dir, self.operator_in_dir))[0],
                        ),
                        series_dir,
                    )
                    for series_dir in series_dirs
                ]
                for future in as_completed(futures):
                    download_series_list.append(future.result())

        # Download the requested data
        logging.info(f"Downloading {len(download_series_list)} series.")
        with ThreadPoolExecutor(max_workers=self.parallel_downloads) as executor:
            futures = [
                executor.submit(
                    self.download_function, series
                )  # Download function is being set in the constructor
                for series in download_series_list
            ]
            for future in as_completed(futures):
                pass

        # Check if target directories are empty
        for series in download_series_list:
            if len(os.listdir(series.target_dir)) == 0:
                raise ValueError(
                    f"Download of referenced data for series {series.series_instance_uid} failed! Target directory is empty."
                )
