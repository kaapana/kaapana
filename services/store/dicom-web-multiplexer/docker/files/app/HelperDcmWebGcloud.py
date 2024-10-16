import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Response
from google.auth.transport import requests
from google.oauth2 import service_account
from kaapanapy.logger import get_logger
from pydantic import BaseModel

logger = get_logger(__file__)


class DicomStoreMetrics(BaseModel):
    name: str
    studyCount: int | None = None
    seriesCount: int | None = None
    instanceCount: int | None = None
    structuredStorageSizeBytes: int | None = None
    blobStorageSizeBytes: int | None = None


class StudyMetrics(BaseModel):
    study: str
    structuredStorageSizeBytes: int
    blobStorageSizeBytes: int
    instanceCount: int
    seriesCount: int


class SeriesMetrics(BaseModel):
    series: str
    structuredStorageSizeBytes: int
    blobStorageSizeBytes: int
    instanceCount: int


class HelperDcmWebGcloud:
    # https://cloud.google.com/healthcare-api/docs/dicom#search_transaction
    INSTANCE_LIMIT = 1000
    SERIES_LIMIT = 100

    def __init__(
        self,
        dcmweb_endpoint: str,
        service_account_info: Dict[str, str],
    ):
        self.dcmweb_endpoint = dcmweb_endpoint
        self.rs_endpoint = f"{self.dcmweb_endpoint}/dicomWeb"
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=[
                "https://www.googleapis.com/auth/cloud-platform"
            ],  # TODO maybe scope could be adjusted and limited
        )
        self.session = requests.AuthorizedSession(credentials=credentials)

    def __str__(self):
        return self.dcmweb_endpoint

    def _make_request(
        self, url: str, params: Dict[str, Any] | None = None
    ) -> Optional[List[Dict]]:
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except ValueError as e:
            logger.error(f"JSON decoding failed: {e}")
        except Exception as e:
            logger.error(f"Response: {response.status_code} - {response.text}")
            logger.error(f"Request error occurred: {e}")
        return None

    def check_reachability(self) -> bool:
        for i in range(10):
            try:
                metrics = self.dicom_store_metrics()
                if metrics is None:
                    return False

                if metrics.studyCount is None:
                    logger.error("Empty dicom store.")
                    return False

                return True
            except Exception as e:
                logger.error(f"Connecting to PACS failed: {e}. Retry {i}")
                time.sleep(1)

        logger.error(
            f"Dcmweb endpoint: {self.dcmweb_endpoint} is not available or wrong credentials."
        )
        return False

    def check_if_series_in_archive(self, series_uid: str) -> bool:
        for attempt in range(1, 31):
            series = self.search_for_series({"SeriesInstanceUID": series_uid})
            if series is not None:
                return True
            logger.error(
                f"Attempt {attempt}/30: Error checking for series {series_uid} in PACS."
            )
            time.sleep(2)

        logger.error(f"Series {series_uid} not found in PACS after 30 attempts.")
        return False

    def downloadSeries(
        self,
        series_uid: str,
        target_dir: Path,
        expected_object_count=None,
        include_series_dir: Optional[bool] = False,
    ) -> bool:
        instances = self.search_for_instances({"SeriesInstanceUID": series_uid})
        if instances is None:
            logger.error(f"Failed to request series UID: {series_uid}")
            return False

        object_uids = [
            (
                obj["0020000D"]["Value"][0],  # StudyInstanceUID
                obj["00080018"]["Value"][0],  # SOPInstanceUID
            )
            for obj in instances
        ]

        if include_series_dir:
            target_dir /= series_uid
        target_dir.mkdir(parents=True, exist_ok=True)

        if expected_object_count is not None and expected_object_count > len(
            object_uids
        ):
            if len(object_uids) == 1 and object_uids[0][-1] is not None:
                if expected_object_count <= int(object_uids[0][-1]):
                    print(
                        f"len(objectUIDList) {len(object_uids)} AND expected_object_count {expected_object_count} <= NumberOfFrames {object_uids[0][-1]} --> success!"
                    )
                else:
                    raise ValueError(
                        f"{len(object_uids)=} but NumberOfFrames is {object_uids[0][-1]} --> unknown DICOM tag situation -> abort"
                    )
            else:
                raise ValueError(
                    f"expected_object_count {expected_object_count} > len(objectUIDList) {len(object_uids)} --> not all expected objects have been found -> abort"
                )
        elif expected_object_count is not None:
            print(
                f"expected_object_count {expected_object_count} <= len(objectUIDList) {len(object_uids)} --> success!"
            )

        for study_uid, object_uid in object_uids:
            if not self.downloadObject(
                study_uid=study_uid,
                series_uid=series_uid,
                object_uid=object_uid,
                target_dir=target_dir,
            ):
                return False

        return True

    def downloadObject(
        self,
        study_uid: str,
        series_uid: str,
        object_uid: str,
        target_dir: Path,
    ) -> bool:
        url = f"{self.rs_endpoint}/studies/{study_uid}/series/{series_uid}/instances/{object_uid}"
        headers = {"Accept": "application/dicom; transfer-syntax=*"}

        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
        except Exception as ex:
            logger.error(f"Download of object was not successful: {ex}")
            logger.error(f"SeriesUID: {series_uid}")
            logger.error(f"StudyUID: {study_uid}")
            logger.error(f"ObjectUID: {object_uid}")
            logger.error(f"Status code: {response.status_code}")
            logger.error(f"Response content: {response.content}")
            return False

        filename = object_uid + ".dcm"
        filepath = target_dir / filename
        with open(filepath, "wb") as f:
            f.write(response.content)
        return True

    def thumbnail(self, study_uid: str, series_uid: str) -> bool:
        url = f"{self.rs_endpoint}/studies/{study_uid}/series/{series_uid}/instances"        
        try:
            logger.info("Get instances")
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            logger.info(response.content)
            instances = response.json()
            instance = sorted(
                instances, key=lambda x: x.get("00200013", {"Value": [0]})["Value"][0]
            )[len(instances) // 2]
            object_uid = instance["00080018"]["Value"][0]


            url = f"{self.rs_endpoint}/studies/{study_uid}/series/{series_uid}/instances/{object_uid}/rendered"
            headers = {"Accept": "image/png"}
            logger.info(f"Get instance: {url}, {headers}")
            response = self.session.get(url, headers=headers, timeout=5)
            response.raise_for_status()

            return response

        except Exception as e:
            logger.error("Download of thumbnail was not successful")
            logger.error(f"URL: {url}")
            logger.error(f"StudyUID: {study_uid}")
            logger.error(f"SeriesUID: {series_uid}")
            logger.error(f"Status code: {response.status_code}")
            logger.error(e)
            logger.error(traceback.format_exc())
            return Response(content="Cannot retrieve thumbnail", status_code=404)

    def dicom_store_metrics(self) -> DicomStoreMetrics | None:
        url = f"{self.dcmweb_endpoint}:getDICOMStoreMetrics"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            metrics = DicomStoreMetrics.model_validate(response.json())
            return metrics
        except Exception as e:
            logger.error("Retrieval of dicom store metrics was not successful")
            logger.error(f"URL: {url}")
            logger.error(f"Status code: {response.status_code}")
            logger.error(e)
            return None

    def study_metrics(self, study_uid: str) -> StudyMetrics | None:
        url = f"{self.rs_endpoint}/studies/{study_uid}:getStudyMetrics"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            metrics = StudyMetrics.model_validate(response.json())
            return metrics
        except Exception as e:
            logger.error("Retrieval of study metrics was not successful")
            logger.error(f"URL: {url}")
            logger.error(f"Status code: {response.status_code}")
            logger.error(e)
            return None

    def series_metrics(self, study_uid: str, series_uid: str) -> SeriesMetrics | None:
        url = f"{self.rs_endpoint}/studies/{study_uid}/series/{series_uid}:getSeriesMetrics"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            metrics = SeriesMetrics.model_validate(response.json())
            return metrics
        except Exception as e:
            logger.error("Retrieval of series metrics was not successful")
            logger.error(f"URL: {url}")
            logger.error(f"Status code: {response.status_code}")
            logger.error(e)
            return None

    def search_instances_of_study(self, study_uid: str) -> List[Dict] | None:
        metrics = self.study_metrics(study_uid=study_uid)
        if not metrics:
            logger.error(f"Couldn't retrieve information about the study: {study_uid}")
            return None

        all_instances = []
        try:
            for i in range((metrics.instanceCount // self.INSTANCE_LIMIT) + 1):
                offset = i * self.INSTANCE_LIMIT
                url = f"{self.rs_endpoint}/studies/{study_uid}/instances"
                response = self.session.get(url, params={"offset": offset})
                all_instances.extend(response.json())
            return all_instances
        except Exception as ex:
            logger.error(f"Retrieval of dicom store details was not successful: {ex}")
            logger.error(f"URL: {url}")
            logger.error(f"Status code: {response.status_code}")
            logger.error(ex)
            return None

    def search_instances_of_series(
        self, study_uid: str, series_uid: str
    ) -> List[Dict] | None:
        metrics = self.series_metrics(study_uid=study_uid, series_uid=series_uid)
        if not metrics:
            logger.error(
                f"Couldn't retrieve information about the series: {series_uid}"
            )
            return None

        all_instances = []
        try:
            for i in range((metrics.instanceCount // self.INSTANCE_LIMIT) + 1):
                offset = i * self.INSTANCE_LIMIT
                url = f"{self.rs_endpoint}/studies/{study_uid}/series/{series_uid}/instances"
                response = self.session.get(url, params={"offset": offset})
                response.raise_for_status()
                all_instances.extend(response.json())
            return all_instances
        except Exception as ex:
            logger.error(f"Retrieval of dicom store details was not successful: {ex}")
            logger.error(f"URL: {url}")
            logger.error(f"Status code: {response.status_code}")
            logger.error(ex)

    def search_series_of_study(self, study_uid: str) -> List[Dict] | None:
        metrics = self.study_metrics(study_uid=study_uid)
        if not metrics:
            logger.error(f"Couldn't retrieve information about the study: {study_uid}")
            return

        all_series = []
        try:
            for i in range((metrics.seriesCount // self.SERIES_LIMIT) + 1):
                offset = i * self.SERIES_LIMIT
                url = f"{self.rs_endpoint}/studies/{study_uid}/series"
                response = self.session.get(url, params={"offset": offset})
                response.raise_for_status()
                all_series.extend(response.json())
            return all_series
        except Exception as ex:
            logger.error(f"Retrieval of dicom store details was not successful: {ex}")
            logger.error(f"URL: {url}")
            logger.error(f"Status code: {response.status_code}")
            logger.error(ex)

    def search_for_series(self, search_filters={}) -> List[Dict] | None:
        all_series = []
        offset = 0
        try:
            while True:
                url = f"{self.rs_endpoint}/series"
                response = self.session.get(
                    url, params={"offset": offset, **search_filters}
                )
                response.raise_for_status()
                series = response.json()
                all_series.extend(series)
                if len(series) < self.SERIES_LIMIT:
                    break
                offset += self.SERIES_LIMIT
            return all_series
        except Exception as ex:
            logger.error(f"Retrieval of dicom store details was not successful: {ex}")
            logger.error(f"URL: {url}")
            logger.error(f"Status code: {response.status_code}")
            logger.error(ex)

    def search_for_instances(self, search_filters={}) -> List[Dict] | None:
        all_instances = []
        offset = 0
        try:
            while True:
                url = f"{self.rs_endpoint}/instances"
                response = self.session.get(
                    url, params={"offset": offset, **search_filters}
                )
                response.raise_for_status()
                instances = response.json()
                all_instances.extend(instances)
                if len(instances) < self.INSTANCE_LIMIT:
                    break
                offset += self.INSTANCE_LIMIT
            return all_instances
        except Exception as ex:
            logger.error(f"Retrieval of dicom store details was not successful: {ex}")
            logger.error(f"URL: {url}")
            logger.error(f"Status code: {response.status_code}")
            logger.error(ex)
