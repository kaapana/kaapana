import logging
import os
from os.path import join
from pathlib import Path
from typing import List

import json
import time
import pydicom
import requests
from dicomweb_client.api import DICOMwebClient
from io import BytesIO
from typing import List
from os.path import join
from pathlib import Path
from kaapana.blueprints.kaapana_global_variables import (
    OIDC_CLIENT_SECRET,
    SERVICES_NAMESPACE,
    SYSTEM_USER_PASSWORD,
)
from requests_toolbelt.multipart import decoder
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEFAULT_DICOM_WEB_RS_ENDPOINT = (
    f"http://dicom-web-filter-service.{SERVICES_NAMESPACE}.svc:8080"
)
DEFAULT_DICOM_WEB_URI_ENDPOINT = (
    f"http://dicom-web-filter-service.{SERVICES_NAMESPACE}.svc:8080/wado-uri/wado"
)


def get_dcmweb_helper(
    application_entity: str = "KAAPANA",
    dag_run=None,
    dcmweb_endpoint=None,
    service_account_info=None,
):
    if dcmweb_endpoint:
        try:
            # Check if external_pacs extension was installed
            from external_pacs.HelperDcmWebGcloud import HelperDcmWebGcloud
            from external_pacs.utils import get_k8s_secret, hash_secret_name

            secret_name = hash_secret_name(name=dcmweb_endpoint)
            if not service_account_info:
                service_account_info = get_k8s_secret(secret_name)
            if not service_account_info:
                raise FileNotFoundError(f"Cannot retrieve secret for {dcmweb_endpoint}")

            if "google" in dcmweb_endpoint and service_account_info:
                return HelperDcmWebGcloud(
                    dcmweb_endpoint=dcmweb_endpoint,
                    service_account_info=service_account_info,
                )
            else:
                logger.error(f"Unsupported dcmweb_endpoint: {dcmweb_endpoint}")
                exit(1)

        except ModuleNotFoundError:
            logger.error(
                "There is no external helper installed - see extensions external-pacs"
            )
            exit(1)

        except Exception:
            logger.error(f"Unknown dcmweb_endpoint: {dcmweb_endpoint}")
            exit(1)
    else:
        return HelperDcmWeb(application_entity=application_entity, dag_run=dag_run)


class DcmWebException(Exception):
    pass


class HelperDcmWeb:
    """
    Helper class for making authorized requests against a dicomweb server.
    """

    def __init__(
        self,
        dcmweb_rs_endpoint: str = DEFAULT_DICOM_WEB_RS_ENDPOINT,
        dcmweb_uri_endpoint: str = DEFAULT_DICOM_WEB_URI_ENDPOINT,
        dag_run: dict = None,
        username: str = None,
        access_token: str = None,
    ):
        """Initialize the HelperDcmWeb class.

        Args:
            dcmweb_rs_endpoint (str, optional): Dicomweb RESTful services endpoint. Defaults to DEFAULT_DICOM_WEB_RS_ENDPOINT.
            dcmweb_uri_endpoint (str, optional): Dicomweb URI endpoint. Defaults to DEFAULT_DICOM_WEB_URI_ENDPOINT.
            dag_run (dict, optional): The dag_run object. Defaults to None.
            username (str, optional): The username of the user who started the dag. Defaults to None.
            access_token (str, optional): The access token of the user. Defaults to None.
        """
        assert dag_run or username or access_token
        self.dcmweb_rs_endpoint = dcmweb_rs_endpoint
        self.dcmweb_uri_endpoint = dcmweb_uri_endpoint
        self.system_user = "system"
        self.system_user_password = SYSTEM_USER_PASSWORD
        self.client_secret = OIDC_CLIENT_SECRET
        self.client_id = "kaapana"

        ### Determine user

        if username:
            self.username = username
        elif dag_run:

            conf_data = dag_run.conf
            try:
                self.username = conf_data["form_data"].get("username")
            except KeyError:
                logger.debug(dag_run)
                logger.debug(dag_run.dag)
                tags = dag_run.dag.tags
                logger.debug(tags)
                if "service" in tags:
                    self.username = self.system_user
                    logger.info("Task belongs to a service dag-run")
        else:
            assert access_token
            self.username = None

        ### Set access token for requests to dicomweb server
        if access_token:
            self.access_token = access_token
        elif self.username == self.system_user:
            self.access_token = self.get_system_user_token()
        else:
            self.access_token = self.impersonate_user()
        self.auth_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "x-forwarded-access-token": self.access_token,
        }
        self.client = DICOMwebClient(
            url=self.dcmweb_rs_endpoint,
            headers=self.auth_headers,
        )
        self.session = requests.Session()
        self.session.headers.update(self.auth_headers)

    def get_system_user_token(
        self,
        ssl_check: bool = False,
    ) -> str:
        """Get the access token for the system user.

        Args:
            ssl_check (bool, optional): Flag to check SSL certificate. Defaults to False.

        Returns:
            str: The access token for the system user.
        """
        payload = {
            "username": self.system_user,
            "password": self.system_user_password,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "password",
        }
        url = f"http://keycloak-external-service.admin.svc:80/auth/realms/{self.client_id}/protocol/openid-connect/token"
        r = requests.post(url, verify=ssl_check, data=payload)
        access_token = r.json()["access_token"]
        return access_token

    def impersonate_user(self) -> str:
        """Impersonate a user by exchanging the system user token for an impersonated user token.

        Returns:
            str: The impersonated user token.
        """
        admin_access_token = self.get_system_user_token()
        url = f"http://keycloak-external-service.admin.svc:80/auth/realms/{self.client_id}/protocol/openid-connect/token"
        data = {
            "client_id": self.client_id,
            "client_secret": OIDC_CLIENT_SECRET,
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": admin_access_token,  # Replace with your actual subject_token
            "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "audience": "kaapana",
            "requested_subject": self.username,
        }

        r = requests.post(url, data=data, verify=False)
        impersonated_access_token = r.json()["access_token"]
        return impersonated_access_token

    def check_if_series_in_archive(self, seriesUID: str, studyUID: str) -> bool:
        """This function checks if a series exists in the archive.

        Args:
            seriesUID (str): Series Instance UID
            studyUID (str): Study Instance UID

        Returns:
            bool: True if the series exists in the archive, False otherwise
        """

        url = f"{self.dcmweb_rs_endpoint}/studies/{studyUID}/series"
        payload = {"SeriesInstanceUID": seriesUID}
        response = self.session.get(url, params=payload)

        # If empty the status code is 204
        return response.status_code == 200

    def check_if_series_is_rejected(self, seriesUID: str, studyUID: str) -> bool:
        """This function checks if a series is rejected from the PACS.

        Args:
            seriesUID (str): Series Instance UID.
            studyUID (str): Study Instance UID.

        Returns:
            bool: True if the series is rejected from the PACS, False otherwise.
        """

        url = f"{self.dcmweb_rs_endpoint}/reject/studies/{studyUID}/series"
        payload = {"SeriesInstanceUID": seriesUID}
        response = self.session.get(url, params=payload)

        # If empty the status code is 204
        return response.status_code == 200

    def check_if_study_in_archive(self, studyUID: str) -> bool:
        """This function checks if a study exists in the archive.

        Args:
            studyUID (str): Study Instance UID of the study to check.

        Returns:
            bool: True if the study exists in the archive, False otherwise.
        """

        url = f"{self.dcmweb_rs_endpoint}/studies"
        payload = {"StudyInstanceUID": studyUID}
        response = self.session.get(url, params=payload)

        # If empty the status code is 204
        return response.status_code == 200

    def __save_dicom_file(self, part: decoder.BodyPart, target_dir: str, index: int):
        """This function saves a DICOM file to the target directory.

        Args:
            part (decoder.BodyPart): DICOM file to save from the multipart message.
            target_dir (str): Target directory to save the DICOM file.
            index (int): Index of the DICOM file in the multipart message.

        """

        dicom_file = pydicom.dcmread(BytesIO(part.content))

        try:
            instance_number = dicom_file.InstanceNumber
        except AttributeError:
            instance_number = index

        file_path = os.path.join(target_dir, f"{instance_number}.dcm")
        dicom_file.save_as(file_path)

    def download_series_slicewise(
        self,
        study_uid: str = None,
        series_uid: str = None,
        target_dir: str = None,
        include_series_dir: bool = False,
    ) -> bool:
        """This function downloads a series from the DICOMWeb server slice-wise. It sends a GET request to the DICOMWeb server to retrieve the series and saves the DICOM files to the target directory.
        Args:
            study_uid (str, optional): Study Instance UID of the series. Defaults to None.
            series_uid (str, optional): Series Instance UID of the series. Defaults to None.
            target_dir (str, optional): Target directory to save the DICOM files. Defaults to None.
            include_series_dir (bool, optional): Flag to include the series UID as a subdirectory in the target directory. Defaults to False.

        Returns:
            bool: True if the series was downloaded successfully, False otherwise.
        """

        # Check if study_uid is provided, if not get it from metadata of given series
        if not study_uid:
            logger.warning("Study UID not provided")
            study_uid = self.__get_study_uid_by_series_uid(series_uid)
            if not study_uid:
                logger.error("Study UID not found")
                return False

        # Create target directory
        if include_series_dir:
            target_dir = join(target_dir, series_uid)
        Path(target_dir).mkdir(parents=True, exist_ok=True)

        # Get all instances of the series
        instances = self.get_instances_of_series(study_uid, series_uid)

        # Download all objects in the series
        for instance in instances:
            instance_uid = instance["00080018"]["Value"][0]
            url = f"{self.dcmweb_uri_endpoint}"
            params = {
                "requestType": "WADO",
                "studyUID": study_uid,
                "seriesUID": series_uid,
                "objectUID": instance_uid,
            }
            response = self.session.get(url, params=params)
            response.raise_for_status()

            with open(join(target_dir, f"{instance_uid}.dcm"), "wb") as f:
                f.write(response.content)

        return True

    def download_series(
        self,
        study_uid: str = None,
        series_uid: str = None,
        target_dir: str = None,
        expected_object_count: int = None,
        include_series_dir: bool = False,
    ) -> bool:
        """This function downloads a series from the DICOMWeb server. It sends a GET request to the DICOMWeb server to retrieve the series and saves the DICOM files to the target directory.

        Args:
            study_uid (str, optional): Study Instance UID of the series. Defaults to None.
            series_uid (str, optional): Series Instance UID of the series. Defaults to None.
            target_dir (str, optional): Target directory to save the DICOM files. Defaults to None.
            expected_object_count (int, optional): The expected number of objects in the series. Defaults to None.
            include_series_dir (bool, optional): Flag to include the series UID as a subdirectory in the target directory. Defaults to False.

        Returns:
            bool: True if the series was downloaded successfully, False otherwise.
        """

        # Check if study_uid is provided, if not get it from metadata of given series
        if not study_uid:
            study_uid = self.__get_study_uid_by_series_uid(series_uid)
            if not study_uid:
                return False

        # Create target directory
        if include_series_dir:
            target_dir = join(target_dir, series_uid)
        Path(target_dir).mkdir(parents=True, exist_ok=True)

        # If expected_object_count is provided, check if it matches the number of objects in the series
        if not expected_object_count is None:
            object_uid_list = self.__get_object_uid_list(study_uid, series_uid)
            if not object_uid_list:
                raise Exception("Error in getting object UID list")

            if not self.__validate_object_count(expected_object_count, object_uid_list):
                raise Exception(
                    f"Error in validating object count! HelperDcmWeb: {expected_object_count=} ; {len(object_uid_list)=} ; {object_uid_list=}"
                )

        num_retries = 10
        for i in range(num_retries):
            try:
                url = (
                    f"{self.dcmweb_rs_endpoint}/studies/{study_uid}/series/{series_uid}"
                )
                response = self.session.get(url)
                response.raise_for_status()

                multipart_data = decoder.MultipartDecoder.from_response(
                    response=response
                )

                del response
                with ThreadPoolExecutor() as executor:
                    for index, part in enumerate(multipart_data.parts):
                        executor.submit(self.__save_dicom_file, part, target_dir, index)
                    del part
                    del multipart_data

                if i > 0:
                    logger.info(
                        f"Successfully downloaded series {series_uid} of study {study_uid} after {i} retries"
                    )
                return True

            except Exception as e:
                logger.error(
                    f"Error downloading series {series_uid} of study {study_uid}: {e}"
                )
                if i < num_retries - 1:
                    logger.info(
                        f"Retrying download of series {series_uid} of study {study_uid}"
                    )
                    # Wait for 5 seconds before retrying
                    time.sleep(5)
                    continue
                else:
                    # Last try: try to download the series slice-wise
                    if self.download_series_slicewise(
                        study_uid=study_uid,
                        series_uid=series_uid,
                        target_dir=target_dir,
                        include_series_dir=include_series_dir,
                    ):
                        logger.info(
                            f"Successfully downloaded series {series_uid} of study {study_uid} slice-wise"
                        )
                        return True

                    logger.error(
                        f"Failed to download series {series_uid} of study {study_uid} after {num_retries} retries"
                    )
                    return False

        return True

    def __get_study_uid_by_series_uid(self, series_uid: str) -> str:
        """This function retrieves the Study Instance UID of a series.

        Args:
            series_uid (str): Series Instance UID of the series.

        Returns:
            str: Study Instance UID of the series.
        """
        url = f"{self.dcmweb_rs_endpoint}/series"
        response = self.session.get(url, params={"SeriesInstanceUID": series_uid})

        if response.status_code == 200:
            response_json = response.json()
            study_uid = response_json[0]["0020000D"]["Value"][0]
            logger.info(
                f"Looked up study UID {study_uid} for series UID {series_uid} (Could potentially be wrong)"
            )
            return study_uid
        else:
            response.raise_for_status()
            return None

    def __get_object_uid_list(self, study_uid: str, series_uid: str) -> list:
        """This function retrieves the list of object UIDs in a series.

        Args:
            study_uid (str): Study Instance UID of the series.
            series_uid (str): Series Instance UID of the series.

        Returns:
            list: List of object UIDs in the series.
        """
        url = f"{self.dcmweb_rs_endpoint}/studies/{study_uid}/series/{series_uid}/instances"
        httpResponse = self.session.get(url)
        if httpResponse.status_code == 200:
            response = httpResponse.json()
            return [
                (
                    resultObject["0020000D"]["Value"][0],  # StudyInstanceUID
                    resultObject["00080018"]["Value"][0],  # SOPInstanceUID
                    resultObject.get("00280008", {}).get("Value", [None])[
                        0
                    ],  # NumberOfFrames
                )
                for resultObject in response
            ]
        else:
            response.raise_for_status()
            return None

    def __validate_object_count(
        self, expected_object_count: int, object_uid_list: list
    ) -> bool:
        """This function validates if the expected object count matches the number of objects in the series.

        Args:
            expected_object_count (int): The expected number of objects in the series.
            object_uid_list (_type_): The list of objects in the series.

        Returns:
            bool: True if the expected object count matches the number of objects in the series, False otherwise.
        """
        if expected_object_count is not None and expected_object_count > len(
            object_uid_list
        ):
            first_object_frames = object_uid_list[0][-1]
            if len(object_uid_list) == 1 and first_object_frames is not None:
                if expected_object_count <= int(first_object_frames):
                    print("Success: Expected object count matches number of frames.")
                else:
                    raise ValueError("Expected object count exceeds number of frames.")
            else:
                raise ValueError("Not all expected objects have been found.")
        elif expected_object_count is not None:
            print("Expected object count is within the range of object list length.")
        return True

    def reject_study(self, study_uid: str) -> requests.Response:
        """This function rejects a study from the PACS. It sends a POST request to the DICOMWeb server to reject the study.

        Args:
            study_uid (str): Study Instance UID of the study to reject

        Returns:
            Response: The response object returned by the DICOMWeb server.
        """
        url = f"{self.dcmweb_rs_endpoint}/studies/{study_uid}/reject/113001^DCM"
        response = self.session.post(url, verify=False)
        if response.status_code == 404:
            if "errorMessage" in response.json():
                logger.error(f"Some error occurred: {response.json()['errorMessage']}")
                return response
        response.raise_for_status()
        return response

    def delete_study(self, study_uid: str) -> requests.Response:
        """This function deletes a study from the PACS. It first rejects the study and then deletes it.

        Args:
            study_uid (str): Study Instance UID of the study to delete

        Returns:
            Response: The response object returned by the DICOMWeb server.
        """
        if not self.check_if_study_in_archive(study_uid):
            logger.info(f"Study {study_uid} does not exist in PACS")
            return None

        self.reject_study(study_uid)

        url = f"{self.dcmweb_rs_endpoint}/studies/{study_uid}"
        response = self.session.delete(url)

        if response.status_code == 404:
            if "errorMessage" in response.json():
                logger.error(f"Some error occurred: {response.json()['errorMessage']}")
                return response
        response.raise_for_status()
        logger.info(f"Study {study_uid} deleted")

        return response

    def get_instances_of_study(self, study_uid: str) -> List[dict]:
        """This function retrieves all instances of a study from the PACS.

        Args:
            study_uid (str): Study Instance UID of the study to retrieve the instances from.

        Returns:
            List[dict]: List of instances of the study. Each instance is represented as a dictionary containing the instance metadata
        """
        url = f"{self.dcmweb_rs_endpoint}/studies/{study_uid}/instances"
        response = requests.get(url, headers=self.auth_headers)
        if response.status_code == 404:
            return None
        elif response.status_code == 204:
            return []
        else:
            response.raise_for_status()
            return response.json()

    def get_instances_of_series(self, study_uid: str, series_uid: str) -> List[dict]:
        """This function retrieves all instances of a series from the PACS.

        Args:
            study_uid (str): Study Instance UID of the series to retrieve the instances from.
            series_uid (str): Series Instance UID of the series to retrieve the instances from.

        Returns:
            List[dict]: List of instances of the series. Each instance is represented as a dictionary containing the instance metadata
        """
        url = f"{self.dcmweb_rs_endpoint}/studies/{study_uid}/series/{series_uid}/instances"
        response = self.session.get(url)
        if response.status_code == 204:
            return []
        elif response.status_code == 404:
            return None
        else:
            response.raise_for_status()
            return response.json()

    def get_series_of_study(self, study_uid: str) -> List[dict]:
        """This function retrieves all series of a study from the PACS.

        Args:
            study_uid (str): Study Instance UID of the study to retrieve the series from.

        Returns:
            List[dict]: List of series of the study. Each series is represented as a dictionary containing the series metadata
        """
        url = f"{self.dcmweb_rs_endpoint}/studies/{study_uid}/series"
        r = self.session.get(url)
        if r.status_code == 204:
            return []
        elif r.status_code == 404:
            return None
        else:
            r.raise_for_status()
            return r.json()

    def delete_series(self, study_uid: str, series_uids: List[str]):
        """This function deletes a series from the PACS. It first rejects the series and then deletes it.

        Args:
            study_uid (str): Study Instance UID of the series to delete
            series_uids (List[str]): List of Series Instance UIDs to delete
        """
        for series_uid in series_uids:
            if not self.check_if_series_in_archive(series_uid, study_uid):
                logger.info(
                    f"Series {series_uid} with study {study_uid} does not exist in PACS"
                )
                continue

            if self.check_if_series_is_rejected(series_uid, study_uid):
                logger.info(
                    f"Series {series_uid} with study {study_uid} is already rejected"
                )
                continue

            # Reject series
            logger.info(f"Rejecting series {series_uids} in study {study_uid}")

            url = f"{self.dcmweb_rs_endpoint}/studies/{study_uid}/series/{series_uid}/reject/113001^DCM"
            response = self.session.post(url, verify=False)
            response.raise_for_status()

        # Delete all rejected instances
        logger.info(f"Deleting series {series_uids} in study {study_uid}")

        url = f"{self.dcmweb_rs_endpoint}/reject/113001^DCM"
        response = self.session.delete(url, verify=False)
        response.raise_for_status()

    def search_for_series(self, search_filters):
        return self.client.search_for_series(search_filters=search_filters)

    def __encode_multipart_message_part(self, boundary: str, payload: bytes) -> bytes:
        """This function encodes the DICOM file as a part of the multipart message.

        Args:
            boundary (str): The boundary string used to separate the parts of the multipart message.
            payload (bytes): The DICOM file to encode.

        Returns:
            bytes: The encoded part of the multipart message containing the DICOM file.
        """
        return (
            f"--{boundary}\r\nContent-Type: application/dicom\r\n\r\n".encode("utf-8")
            + payload
            + b"\r\n"
        )

    def __retrieve_clinical_trial_protocol_info(
        self, dicom_file: pydicom.FileDataset
    ) -> dict:
        """This function retrieves the clinical trial protocol information from the DICOM file. Later this information is appended to the request as query parameters.
           This information will be used to map the uploaded DICOM files to the clinical trial protocol in the dicom-web-filter service.

        Args:
            dicom_file (pydicom.FileDataset): The DICOM file to extract the clinical trial protocol information from.

        Returns:
            dict: A dictionary containing the clinical trial protocol information extracted from the DICOM file
        """

        # read 0012,0020 Clinical Trial Protocol ID
        tag = dicom_file.get(0x00120020)
        protocol_id = tag.value if tag else None

        # read 0012,0021 Clinical Trial Protocol Name
        tag = dicom_file.get(0x00120021)
        protocol_name = tag.value if tag else None

        # read 0012,0031 Clinical Trial Site ID
        tag = dicom_file.get(0x00120031)
        site_id = tag.value if tag else None

        # read 0020,000D Study Instance UID
        tag = dicom_file.get(0x0020000D)
        study_instance_uid = tag.value if tag else None

        return {
            "protocol_id": protocol_id,
            "protocol_name": protocol_name,
            "site_id": site_id,
            "study_instance_uid": study_instance_uid,
        }

    def upload_dcm_files(self, path_to_dicom_files: str) -> None:
        """This function uploads DICOM files to the DICOMWeb server using the DICOMWeb RESTful services. It encodes the DICOM files as a multipart message and sends a POST request to the DICOMWeb server.

        Args:
            path_to_dicom_files (str): The path to the directory containing the DICOM files to upload.

        Raises:
            e: An error occurred while uploading the DICOM files.

        Returns:
            Response: The response object returned by the DICOMWeb server.
        """
        url = f"{self.dcmweb_rs_endpoint}/studies"
        boundary = "0f3cf5c0-70e0-41ef-baef-c6f9f65ec3e1"
        clinical_trial_protocol_info = {}
        body = b""

        for root, _, files in os.walk(path_to_dicom_files):
            for file in files:
                dicom_file_path = os.path.join(root, file)
                dicom_file = pydicom.dcmread(dicom_file_path)

                # Retrieve clinical trial protocol information
                instance_uid = dicom_file.get(0x0020000E).value
                clinical_trial_protocol_info[instance_uid] = (
                    self.__retrieve_clinical_trial_protocol_info(dicom_file)
                )

                # Encode the DICOM file and add to the body
                with BytesIO() as buffer:
                    dicom_file.save_as(buffer)
                    buffer.seek(0)
                    body += self.__encode_multipart_message_part(
                        boundary, buffer.getvalue()
                    )

        body += f"--{boundary}--\r\n".encode("utf-8")
        content_type = f"multipart/related; type=application/dicom; boundary={boundary}"

        response = self.session.post(
            url,
            headers={
                "Content-Type": content_type,
                "Authorization": f"Bearer {self.access_token}",
            },
            data=body,
            # append the clinical trial protocol information to the request
            params={
                "clinical_trial_protocol_info": json.dumps(clinical_trial_protocol_info)
            },
        )

        # Catch any exceptions
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(f"An error occurred: {e}")
            raise e
        else:
            logger.info("DICOM files uploaded successfully")
            return response
