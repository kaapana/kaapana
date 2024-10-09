import glob
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from os import getenv
from os.path import join
from pathlib import Path

import pydicom
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapanapy.helper.HelperOpensearch import HelperOpensearch

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class DownloadSeries:
    series_instance_uid: str
    reference_series_uid: str
    study_instance_uid: str
    target_dir: str


class GetRefSeriesOperator:
    """
    Operator to get DICOM series.

    This operator downloads DICOM series from a given PACS system according to specified search filters.
    The downloading is executed in a structured manner such that the downloaded data is saved to target directories named with the series_uid.
    """

    def __init__(
        self,
        search_policy: str = "reference_uid",  # reference_uid, study_uid, patient_uid
        data_type: str = "dicom",
        dicom_tags: list = [],  # list of dicom tags to filter the series
        parallel_downloads: int = 3,
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
        meta_data = HelperOpensearch.get_series_metadata(
            series_instance_uid=series.reference_series_uid
        )

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
        self,
        path_to_dicom_slice: str,
        workflow_dir: str,
        batch_name: str,
        operator_out_dir: str,
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
            workflow_dir (str): The workflow directory.
            batch_name (str): The batch name.
            operator_out_dir (str): The operator out directory.

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

        target_dir = join(
            workflow_dir,
            batch_name,
            series_instance_uid,
            operator_out_dir,
        )

        os.makedirs(target_dir, exist_ok=True)

        return DownloadSeries(
            series_instance_uid=series_instance_uid,
            reference_series_uid=reference_series_uid,
            study_instance_uid=study_instance_uid,
            target_dir=target_dir,
        )

    def get_files(self, workflow_dir, batch_name, operator_in_dir, operator_out_dir):
        """Download series from PACS or Opensearch.

        Args:
            ds (dict): The input dictionary.

        Raises:
            ValueError: If the download failed.
        """
        logger.info("Starting module GetRefSeriesOperator")
        self.dcmweb_helper = HelperDcmWeb()

        series_dirs = glob.glob(join("/", workflow_dir, batch_name, "*"))

        download_series_list = []

        if self.search_policy == "reference_uid":
            # Prepare the download
            with ThreadPoolExecutor(max_workers=self.parallel_downloads) as executor:
                futures = [
                    executor.submit(
                        self.prepare_download,
                        join(
                            series_dir,
                            operator_in_dir,
                            os.listdir(join(series_dir, operator_in_dir))[0],
                        ),
                        workflow_dir,
                        batch_name,
                        operator_out_dir,
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


if __name__ == "__main__":
    workflow_dir = getenv("WORKFLOW_DIR", None)
    assert os.path.exists(
        workflow_dir
    ), f"Workflow directory {workflow_dir} does not exist!"

    batch_name = getenv("BATCH_NAME", None)
    assert batch_name is not None, "Batch name is not set!"

    operator_in_dir = getenv("OPERATOR_IN_DIR", None)
    assert operator_in_dir is not None, "Operator in directory is not set!"

    operator_out_dir = getenv("OPERATOR_OUT_DIR", None)
    assert operator_out_dir is not None, "Operator out directory is not set!"

    search_policy = getenv("SEARCH_POLICY", "reference_uid")
    data_type = getenv("DATA_TYPE", "dicom")
    dicom_tags = json.loads(getenv("DICOM_TAGS", "[]"))
    parallel_downloads = int(getenv("PARALLEL_DOWNLOADS", 3))

    logger.info(f"Worflow dir: {workflow_dir}")
    logger.info(f"Batch name: {batch_name}")
    logger.info(f"Operator in dir: {operator_in_dir}")
    logger.info(f"Operator out dir: {operator_out_dir}")
    logger.info(f"Search policy: {search_policy}")
    logger.info(f"Data type: {data_type}")
    logger.info(f"DICOM tags: {dicom_tags}")
    logger.info(f"Parallel downloads: {parallel_downloads}")

    # Start the operator
    get_ref_series_operator = GetRefSeriesOperator(
        search_policy=search_policy,
        data_type=data_type,
        dicom_tags=dicom_tags,
        parallel_downloads=parallel_downloads,
    )

    get_ref_series_operator.get_files(
        workflow_dir=workflow_dir,
        batch_name=batch_name,
        operator_in_dir=operator_in_dir,
        operator_out_dir=operator_out_dir,
    )
