import ast
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
from kaapanapy.helper import load_workflow_config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class DownloadSeries:
    series_instance_uid: str
    reference_series_uid: str
    study_instance_uid: str
    target_dir: str


def build_opensearch_query(modalities: list = [], custom_tags: list = []) -> dict:
    """Build an OpenSearch query based on the given modalities and custom tags.

    Args:
        modalities (list, optional): Given modalities. Defaults to []. Must be list of strings.
        custom_tags (list, optional): Given custom tags. Defaults to []. Must be list of strings.

    Returns:
        dict: The OpenSearch query.
    """
    # Base of the OpenSearch query
    query = {"bool": {"must": []}}

    # If 'modalities' is filled, we add a condition to check "00080060 Modality_keyword"
    if modalities:
        # If only one modality is given, we add a 'match' query
        if len(modalities) == 1:
            query["bool"]["must"].append(
                {"match": {"00080060 Modality_keyword": modalities[0]}}
            )
        else:
            # If multiple modalities are given, we add a 'should' query
            query["bool"]["should"] = []
            for modality in modalities:
                query["bool"]["should"].append(
                    {"match": {"00080060 Modality_keyword": modality}}
                )

    # If 'custom_tags' is filled, we add a 'terms_set' query to check "00000000 Tags_keyword" contains all tags
    if custom_tags:
        tags_query = {
            "terms_set": {
                "00000000 Tags_keyword": {
                    "terms": custom_tags,
                    "minimum_should_match_script": {"source": "params.num_terms"},
                }
            }
        }
        query["bool"]["must"].append(tags_query)

    # Return the final query structure
    return query


class GetRefSeriesOperator:
    """
    Operator to get DICOM series.

    This operator downloads DICOM series from a given PACS system according to specified search filters.
    The downloading is executed in a structured manner such that the downloaded data is saved to target directories named with the series_uid.
    """

    def __init__(
        self,
        opensearch_index: str,
        search_policy: str = "reference_uid",
        data_type: str = "dicom",
        search_query: dict = {},
        parallel_downloads: int = 3,
        modalities: list = [],
        custom_tags: list = [],
    ):
        """Initialize the GetRefSeriesOperator.

        Args:
            opensearch_index (str): The opensearch index to search for series metadata.
            search_policy (str, optional): The search policy to filter the series. Can be "reference_uid", "study_uid" or "search_query". Defaults to "reference_uid". "reference_uid" downloads the reference series of a SEG or RTSTRUCT, "study_uid" downloads all series of a study, "search_query" downloads all series based on a search query.
            data_type (str, optional): The type of data to download. Can be "dicom" or "json". Defaults to "dicom".
            search_query (list, optional): The search query for opensearch. Syntax must be the same as for opensearch. Defaults to {}. Must be a bool query (https://opensearch.org/docs/latest/query-dsl/compound/bool).
            parallel_downloads (int, optional): Number of parallel downloads. Defaults to 3.
            modalities (list, optional): List of modalities to filter the series. Defaults to []. Cant be used together with search_query. Only makes sense in conjunction with search_policy="study_uid".
            custom_tags (list, optional): List of custom tags to filter the series. Defaults to []. Cant be used together with search_query. Only makes sense in conjunction with search_policy="study_uid".

        """
        self.opensearch_index = opensearch_index
        assert data_type in ["dicom", "json"], "Unknown data-type!"

        assert search_policy in [
            "reference_uid",
            "study_uid",
            "search_query",
        ], "Unknown search policy!"

        assert (
            search_policy != "search_query" or search_query != {}
        ), "Search query must be set!"

        # To avoid ambiguity:
        # If search query is set, modality and custom tags cannot be set
        assert search_query == {} or (
            modalities == [] and custom_tags == []
        ), "Modality and custom tags cannot be set if search query is set!"

        # If modality is set, search query can't be set
        assert (
            modalities == [] or search_query == {}
        ), "Modality cannot be set if search query is set!"

        # If custom tags are set, search query can't be set
        assert (
            custom_tags == [] or search_query == {}
        ), "Custom tags cannot be set if search query is set!"

        if data_type == "json":
            self.download_function = self.download_metadata_from_opensearch
        elif data_type == "dicom":
            self.download_function = self.download_series_from_pacs

        if modalities != [] or custom_tags != []:
            # Create search query
            self.search_query = build_opensearch_query(
                modalities=modalities, custom_tags=custom_tags
            )
        else:
            self.search_query = search_query

        if self.search_query != {}:
            assert (
                "bool" in self.search_query
            ), "Search query must be a bool query! (https://opensearch.org/docs/latest/query-dsl/compound/bool)"

            logger.info(f"Initial search query: {self.search_query}")

        self.data_type = data_type
        self.parallel_downloads = parallel_downloads
        self.search_policy = search_policy
        self.os_helper = HelperOpensearch()

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
        meta_data = self.os_helper.os_client.get(
            index=self.opensearch_index, id=series.reference_series_uid
        )["_source"]

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
                f"Download of series {series.reference_series_uid} failed! Number of instances does not match number of downloaded files."
            )

        logger.info(f"Number of instances in PACS: {len(instances)}")
        logger.info(f"Number of downloaded files: {len(os.listdir(series.target_dir))}")
        logger.info(
            f"Downloaded series {series.reference_series_uid} to {series.target_dir}"
        )

    def get_ids_of_series(self, path_to_dicom_slice: str) -> str:
        """
        Get all kinds of ids from a dicom file.
        """

        # Load the dicom file
        ds = pydicom.dcmread(join(path_to_dicom_slice))

        study_instance_uid = ds.StudyInstanceUID
        series_instance_uid = ds.SeriesInstanceUID
        patient_id = ds.PatientID

        return series_instance_uid, study_instance_uid, patient_id

    def prepare_download_of_study_series(
        self,
        study_instance_uid: str,
        workflow_dir: str,
        batch_name: str,
        operator_out_dir: str,
    ) -> DownloadSeries:
        """Prepare the download of all series of a study. Means:
        - Find all series of the given study in OpenSearch.
        - Create the target directories for the download.
        - Return a list of DownloadSeries objects, which contains the information needed for the download.

        Args:
            study_instance_uid (str): The study instance uid to download.
            workflow_dir (str): The workflow directory.
            batch_name (str): The batch name.
            operator_out_dir (str): The operator out directory.

        Returns:
            DownloadSeries: Dataclass containing the information needed for the download.
        """

        logger.info(f"Study instance uid: {study_instance_uid}")

        # Check if search query is set
        if self.search_query != {}:
            # Check if "must" is set in search query
            if not "must" in self.search_query["bool"]:
                self.search_query["bool"]["must"] = []

            # Add study_instance_uid to search query
            self.search_query["bool"]["must"].append(
                {"term": {"0020000D StudyInstanceUID_keyword": study_instance_uid}}
            )

            query = self.search_query
        else:
            # Take all series of the given study
            query = {
                "term": {
                    "0020000D StudyInstanceUID_keyword": study_instance_uid,
                }
            }

        logger.info(f"Search query: {query}")

        series_of_study = self.os_helper.execute_opensearch_query(
            index=self.opensearch_index, query=query
        )

        # Extract SeriesInstanceUID from each study
        series_instance_uids = [
            study["_source"]["0020000E SeriesInstanceUID_keyword"]
            for study in series_of_study
        ]

        list_of_series = []

        for series_instance_uid in series_instance_uids:
            target_dir = join(
                workflow_dir,
                batch_name,
                operator_out_dir,
                series_instance_uid,
            )

            os.makedirs(target_dir, exist_ok=True)

            list_of_series.append(
                DownloadSeries(
                    series_instance_uid=series_instance_uid,
                    reference_series_uid=series_instance_uid,
                    study_instance_uid=study_instance_uid,
                    target_dir=target_dir,
                )
            )

        return list_of_series

    def prepare_download_of_ref_series(
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
            operator_out_dir,
        )

        os.makedirs(target_dir, exist_ok=True)

        return DownloadSeries(
            series_instance_uid=series_instance_uid,
            reference_series_uid=reference_series_uid,
            study_instance_uid=study_instance_uid,
            target_dir=target_dir,
        )

    def prepare_download_of_search_query_series(
        self,
        search_query: dict,
        workflow_dir: str,
        batch_name: str,
        operator_out_dir: str,
    ) -> DownloadSeries:
        """Prepare the download of series based on a search_query. Means:
        - Get all series of the given search_query in OpenSearch.
        - Create the target directories for the download.
        - Return a list of DownloadSeries objects, which contains the information needed for the download.


        Args:
            search_query (dict): The search query.
            workflow_dir (str): The workflow directory.
            batch_name (str): The batch name.
            operator_out_dir (str): The operator out directory.

        Returns:
            DownloadSeries: Dataclass containing the information needed for the download.
        """

        logger.info(f"Search query: {search_query}")

        series_of_search_query = self.os_helper.execute_opensearch_query(
            index=self.opensearch_index, query=search_query
        )

        list_of_series = []

        for series in series_of_search_query:
            series_instance_uid = series["_source"][
                "0020000E SeriesInstanceUID_keyword"
            ]
            study_instance_uid = series["_source"]["0020000D StudyInstanceUID_keyword"]

            target_dir = join(
                workflow_dir,
                batch_name,
                series_instance_uid,
                operator_out_dir,
            )

            os.makedirs(target_dir, exist_ok=True)

            list_of_series.append(
                DownloadSeries(
                    series_instance_uid=series_instance_uid,
                    reference_series_uid=series_instance_uid,
                    study_instance_uid=study_instance_uid,
                    target_dir=target_dir,
                )
            )

        return list_of_series

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

        # Check if series_dirs is empty
        if self.search_policy != "search_query":
            assert (
                series_dirs != [] and self.search_policy != "search_query"
            ), "No series in the workflow directory!"

        download_series_list = []

        if self.search_policy == "reference_uid":
            # Prepare the download
            with ThreadPoolExecutor(max_workers=self.parallel_downloads) as executor:
                futures = []
                for series_dir in series_dirs:
                    try:
                        dcm_file = join(
                            series_dir,
                            operator_in_dir,
                            os.listdir(join(series_dir, operator_in_dir))[0],
                        )
                    except FileNotFoundError as e:
                        if getenv("SKIP_EMPTY_REF_DIR", "FALSE").upper() == "TRUE":
                            print(
                                f"Skipping empty directory: {join(series_dir, operator_in_dir)}"
                            )
                            continue
                        else:
                            raise e
                        
                    series_uid = series_dir.split("/")[-1]
                    futures.append(
                        executor.submit(
                            self.prepare_download_of_ref_series,
                            dcm_file,
                            workflow_dir,
                            batch_name,
                            join(series_uid, operator_out_dir),
                        )
                    )

                for future in as_completed(futures):
                    download_series_list.append(future.result())
        elif self.search_policy == "study_uid":

            ids = []
            for series_dir in series_dirs:
                try:
                    dcm_file = join(
                        series_dir,
                        operator_in_dir,
                        os.listdir(join(series_dir, operator_in_dir))[0],
                    )
                except FileNotFoundError as e:
                    if getenv("SKIP_EMPTY_REF_DIR", "FALSE").upper() == "TRUE":
                        print(
                            f"Skipping empty directory: {join(series_dir, operator_in_dir)}"
                        )
                        continue
                    else:
                        raise e
                    
                id = self.get_ids_of_series(dcm_file)
                if id not in ids:
                    ids.append(id)

            download_series_list = []
            for id in ids:
                download_series_list += self.prepare_download_of_study_series(
                    id[1], workflow_dir, batch_name, join(id[0], operator_out_dir)
                )
                
        elif self.search_policy == "search_query":
            download_series_list = self.prepare_download_of_search_query_series(
                self.search_query, workflow_dir, batch_name, operator_out_dir
            )

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

    operator_out_dir = getenv("OPERATOR_OUT_DIR", None)
    assert operator_out_dir is not None, "Operator out directory is not set!"

    custom_tags = ast.literal_eval(getenv("CUSTOM_TAGS", "[]"))
    modalities = ast.literal_eval(getenv("MODALITIES", "[]"))

    search_policy = getenv("SEARCH_POLICY", "reference_uid")

    operator_in_dir = getenv("OPERATOR_IN_DIR", None)
    if not search_policy == "search_query":
        assert operator_in_dir is not None, "Operator in directory is not set!"

    data_type = getenv("DATA_TYPE", "dicom")
    search_query = json.loads(getenv("SEARCH_QUERY", "{}"))
    parallel_downloads = int(getenv("PARALLEL_DOWNLOADS", 3))

    logger.info(f"Worflow dir: {workflow_dir}")
    logger.info(f"Batch name: {batch_name}")
    logger.info(f"Operator in dir: {operator_in_dir}")
    logger.info(f"Operator out dir: {operator_out_dir}")
    logger.info(f"Search policy: {search_policy}")
    logger.info(f"Data type: {data_type}")
    logger.info(f"Search query: {search_query}")
    logger.info(f"Parallel downloads: {parallel_downloads}")
    logger.info(f"Modalities: {modalities}")
    logger.info(f"Custom tags: {custom_tags}")

    workflow_config = load_workflow_config()
    project_form = workflow_config.get("project_form")
    project_index = project_form.get("opensearch_index")

    # Start the operator
    get_ref_series_operator = GetRefSeriesOperator(
        opensearch_index=project_index,
        search_policy=search_policy,
        data_type=data_type,
        search_query=search_query,
        parallel_downloads=parallel_downloads,
        modalities=modalities,
        custom_tags=custom_tags,
    )

    get_ref_series_operator.get_files(
        workflow_dir=workflow_dir,
        batch_name=batch_name,
        operator_in_dir=operator_in_dir,
        operator_out_dir=operator_out_dir,
    )
