import requests
import logging
import os
import json
import time
from dicomweb_client.api import DICOMwebClient
import pydicom
from io import BytesIO
from typing import List
from os.path import join
from pathlib import Path
from kaapana.blueprints.kaapana_global_variables import (
    SERVICES_NAMESPACE,
    OIDC_CLIENT_SECRET,
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


class HelperDcmWeb:
    """
    Helper class for making authorized requests against a dicomweb server.
    """

    def __init__(
        self,
        dcmweb_rs_endpoint: str = DEFAULT_DICOM_WEB_RS_ENDPOINT,
        dcmweb_uri_endpoint: str = DEFAULT_DICOM_WEB_URI_ENDPOINT,
        dag_run=None,
        username: str = None,
        access_token: str = None,
    ):
        """
        :param dcmweb_rs_endpoint: URL to the dicomweb server.
        :param dag_run: Airflow dag object.
        :param username: Username of the keycloak user that wants to communicate with the dicomweb server.
        :access_token: Access token that should be used for communication with the dicomweb server.
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
                tags = dag_run.dag.tags
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
        ssl_check=False,
    ):
        """
        Get access token for the system user.
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

    def impersonate_user(self):
        """
        Get access token for a user via token exchange.
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

    def check_if_series_in_archive(self, seriesUID, studyUID):
        """
        Check if a series exists in the archive
        """

        url = f"{self.dcmweb_rs_endpoint}/studies/{studyUID}/series"
        payload = {"SeriesInstanceUID": seriesUID}
        response = self.session.get(url, params=payload)

        # If empty the status code is 204
        return response.status_code == 200

    def check_if_series_is_rejected(self, seriesUID, studyUID):
        """
        Check if a series exists in the archive
        """

        url = f"{self.dcmweb_rs_endpoint}/reject/studies/{studyUID}/series"
        payload = {"SeriesInstanceUID": seriesUID}
        response = self.session.get(url, params=payload)

        # If empty the status code is 204
        return response.status_code == 200

    def check_if_study_in_archive(self, studyUID):
        """
        Check if a study exists in the archive
        """

        url = f"{self.dcmweb_rs_endpoint}/studies"
        payload = {"StudyInstanceUID": studyUID}
        response = self.session.get(url, params=payload)

        # If empty the status code is 204
        return response.status_code == 200

    def __save_dicom_file(self, part, target_dir, index):

        dicom_file = pydicom.dcmread(BytesIO(part.content))

        try:
            instance_number = dicom_file.InstanceNumber
        except:
            instance_number = index

        file_path = os.path.join(target_dir, f"{instance_number}.dcm")
        dicom_file.save_as(file_path)
        return True

    def download_series_slicewise(
        self,
        study_uid: str = None,
        series_uid: str = None,
        target_dir: str = None,
        include_series_dir: bool = False,
    ) -> bool:

        # Check if study_uid is provided, if not get it from metadata of given series
        if not study_uid:
            study_uid = self.__get_study_uid_by_series_uid(series_uid)
            if not study_uid:
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

        # Download all objects in the series
        # logger.info(f"Downloading series {series_uid} of study {study_uid}")

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
                    futures = []
                    for index, part in enumerate(multipart_data.parts):
                        futures.append(
                            executor.submit(
                                self.__save_dicom_file, part, target_dir, index
                            )
                        )

                    del part
                    del multipart_data

                    for future in futures:
                        result = future.result()
                        if not result:
                            raise Exception("Error in saving DICOM file")

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
        url = f"{self.dcmweb_rs_endpoint}/studies"
        payload = {"SeriesInstanceUID": series_uid}
        response = self.session.get(url, params=payload)
        if response.status_code == 200:
            return response.json()[0]["0020000D"]["Value"][0]
        else:
            response.raise_for_status()
            return None

    def __get_object_uid_list(self, study_uid: str, series_uid: str):
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

    def __validate_object_count(self, expected_object_count: int, object_uid_list):
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

    def reject_study(self, study_uid: str):
        """
        Reject a study
        """
        url = f"{self.dcmweb_rs_endpoint}/studies/{study_uid}/reject/113001^DCM"
        response = self.session.post(url, verify=False)
        response.raise_for_status()
        return response

    def delete_study(self, study_uid: str):
        """
        Reject a study and delete it from the PACS
        """
        if not self.check_if_study_in_archive(study_uid):
            logger.info(f"Study {study_uid} does not exist in PACS")
            return None

        self.reject_study(study_uid)

        url = f"{self.dcmweb_rs_endpoint}/studies/{study_uid}"
        response = self.session.delete(url)
        response.raise_for_status()

        logger.info(f"Study {study_uid} deleted")

        return response

    def get_instances_of_study(self, study_uid):
        """
        Get all instances of a study
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

    def get_instances_of_series(self, study_uid, series_uid):
        """
        Get all instances of a specific series of a specific study
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

    def get_series_of_study(self, study_uid):
        """
        Get all series of a study
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
        """
        Encodes a single part of the multipart message.

        Parameters
        ----------
        boundary: str
            The boundary string to separate parts of the message.
        payload: bytes
            The byte data to include in this part of the multipart message.

        Returns
        -------
        bytes
            The encoded part of the multipart message.
        """
        return (
            f"--{boundary}\r\nContent-Type: application/dicom\r\n\r\n".encode("utf-8")
            + payload
            + b"\r\n"
        )

    def __retrieve_clinical_trial_protocol_info(self, dicom_file) -> dict:

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
        """
        Send individual DICOM instances to the DICOMweb server using the STOW-RS service.

        Parameters:
            path_to_dicom_files (str): Path to the DICOM files to be sent.
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
