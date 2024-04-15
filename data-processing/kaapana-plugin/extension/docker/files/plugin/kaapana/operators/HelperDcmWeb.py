import requests
import logging
import os
import tempfile
import time
import pydicom
from dicomweb_client.api import DICOMwebClient
from typing import List
from os.path import join
from pathlib import Path
from glob import glob
from kaapana.blueprints.kaapana_global_variables import (
    SERVICES_NAMESPACE,
    OIDC_CLIENT_SECRET,
    SYSTEM_USER_PASSWORD,
)


logger = logging.getLogger(__name__)


class DcmWebException(Exception):
    pass


class HelperDcmWeb:
    """
    Helper class for making authorized requests against a dcm4chee archive.
    """

    def __init__(
        self,
        application_entity: str,
        dag_run=None,
        username: str = None,
        access_token: str = None,
    ):
        """
        :param application_entity: Title of the application entity to communicate with
        :param dag_run: Airflow dag object.
        :param username: Username of the keycloak user that wants to communicate with dcm4chee.
        :access_token: Access token that should be used for communication with dcm4chee.
        """
        assert dag_run or username or access_token
        self.dcmweb_endpoint = (
            f"http://dcm4chee-service.{SERVICES_NAMESPACE}.svc:8080/dcm4chee-arc/aets"
        )
        self.application_entity = application_entity
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

        ### Set access token for requests to dcm4chee
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
            url=f"{self.dcmweb_endpoint}/{self.application_entity}/rs",
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

    def set_access_control_id_of_study(self, access_control_id: str):
        """
        Set the access control id of a study in dcm4chee
        """
        url = f"{self.dcmweb_endpoint}/{self.application_entity}/rs/studies/{access_control_id}/access/{access_control_id}"
        r = requests.put(
            url,
            headers=self.auth_headers,
        )
        r.raise_for_status()

    def add_access_control_id_to_ae(self, access_control_id: str):
        """
        Add access control id to an application entity in dcm4chee
        """
        url = f"http://kaapana-backend-service.{SERVICES_NAMESPACE}.svc:5000/aets/{self.application_entity}/access-control-id/{access_control_id}"
        r = requests.put(
            url,
            headers=self.auth_headers,
        )
        r.raise_for_status()

    def check_if_series_in_archive(self, seriesUID):
        """
        Check if a series exists in the archive and belongs to the application entity
        """
        max_tries = 30
        tries = 0
        while tries < max_tries:
            pacs_dcmweb_endpoint = (
                f"{self.dcmweb_endpoint}/{self.application_entity}/rs/instances"
            )
            payload = {"SeriesInstanceUID": seriesUID}
            httpResponse = self.session.get(
                pacs_dcmweb_endpoint, params=payload, timeout=2
            )
            if httpResponse.status_code == 200:
                break
            else:
                tries += 1
                time.sleep(2)
        if tries >= max_tries:
            return False
        else:
            return True

    def downloadSeries(
        self,
        series_uid,
        target_dir,
        expected_object_count=None,
        include_series_dir=False,
    ):
        payload = {"SeriesInstanceUID": series_uid}
        url = f"{self.dcmweb_endpoint}/{self.application_entity}/rs/instances"
        httpResponse = self.session.get(url, params=payload)
        if httpResponse.status_code == 200:
            response = httpResponse.json()
            objectUIDList = []
            for resultObject in response:
                objectUIDList.append(
                    [
                        resultObject["0020000D"]["Value"][0],  # StudyInstanceUID
                        resultObject["00080018"]["Value"][0],  # SOPInstanceUID
                        (
                            resultObject["00280008"]["Value"][0]
                            if "Value" in resultObject["00280008"]
                            else None
                        ),  # NumberOfFrames
                    ]
                )  # objectUID

            if include_series_dir:
                target_dir = join(target_dir, series_uid)
            Path(target_dir).mkdir(parents=True, exist_ok=True)
            print(
                f"HelperDcmWeb: {expected_object_count=} ; {len(objectUIDList)=} ; {objectUIDList=} ; {objectUIDList[0][-1]=}"
            )
            if expected_object_count != None and expected_object_count > len(
                objectUIDList
            ):
                if len(objectUIDList) == 1 and objectUIDList[0][-1] is not None:
                    if expected_object_count <= int(objectUIDList[0][-1]):
                        print(
                            f"len(objectUIDList) {len(objectUIDList)} AND expected_object_count {expected_object_count} <= NumberOfFrames {objectUIDList[0][-1]} --> success!"
                        )
                    else:
                        raise ValueError(
                            f"{len(objectUIDList)=} but NumberOfFrames is {objectUIDList[0][-1]} --> unknown DICOM tag situation -> abort"
                        )
                else:
                    raise ValueError(
                        f"expected_object_count {expected_object_count} > len(objectUIDList) {len(objectUIDList)} --> not all expected objects have been found -> abort"
                    )
            elif expected_object_count != None:
                print(
                    f"expected_object_count {expected_object_count} <= len(objectUIDList) {len(objectUIDList)} --> success!"
                )

            for object_uid in objectUIDList:
                study_uid = object_uid[0]
                object_uid = object_uid[1]
                result = self.downloadObject(
                    study_uid=study_uid,
                    series_uid=series_uid,
                    object_uid=object_uid,
                    target_dir=target_dir,
                )
                if not result:
                    return False

            return True
        else:
            print("################################")
            print("#")
            print("# Can't request series objects from PACS!")
            print(f"# UID: {series_uid}")
            print(f"# Status code: {httpResponse.status_code}")
            print("#")
            print("################################")
            return False

    def downloadObject(self, study_uid, series_uid, object_uid, target_dir):
        payload = {
            "requestType": "WADO",
            "studyUID": study_uid,
            "seriesUID": series_uid,
            "objectUID": object_uid,
            "contentType": "application/dicom",
        }
        url = f"{self.dcmweb_endpoint}/{self.application_entity}/wado"
        response = self.session.get(url, params=payload)
        if response.status_code == 200:
            fileName = object_uid + ".dcm"
            filePath = os.path.join(target_dir, fileName)
            with open(filePath, "wb") as f:
                f.write(response.content)

            return True

        else:
            print("################################")
            print("#")
            print("# Download of requested objectUID was not successful!")
            print(f"# seriesUID: {series_uid}")
            print(f"# studyUID: {study_uid}")
            print(f"# objectUID: {object_uid}")
            print(f"# Status code: {response.status_code}")
            print(f"# Response content: {response.content}")
            print("#")
            print("################################")
            return False

    def reject_study(self, study_uid: str, application_entity: str = None):
        """
        Reject a study
        """
        application_entity = application_entity or self.application_entity
        rejectionURL = f"{self.dcmweb_endpoint}/{application_entity}/rs/studies/{study_uid}/reject/113001%5EDCM"
        response = self.session.post(rejectionURL, verify=False)
        response.raise_for_status()
        return response

    def delete_study(self, study_uid: str):
        logger.info(f"Deleting study {study_uid}")
        if not self.get_instances_of_study(
            study_uid=study_uid, application_entity=self.application_entity
        ):
            logger.warn("Study does not exist on PACS")
            return

        logger.info("1/2: rejecting study")
        response = self.reject_study(study_uid=study_uid)
        logger.info("Awaiting rejection to complete")
        time.sleep(5)
        logger.info("Rejection complete")
        # After the rejection there can be Key Object Selection Document Storage left on the pacs,
        # these will disapear when the study is finaly deleted, so a check
        # may still return results in this spot

        logger.info("2/2: deleting study")
        aet_rejection_stage = "IOCM_QUALITY"
        if not self.get_instances_of_study(
            study_uid=study_uid, application_entity=aet_rejection_stage
        ):
            raise DcmWebException(
                f"Could not find study {study_uid} in aet {aet_rejection_stage}"
            )
        logger.info(f"Found study {study_uid} in aet {aet_rejection_stage}")

        deletionURL = (
            f"{self.dcmweb_endpoint}/{aet_rejection_stage}/rs/studies/{study_uid}"
        )
        logger.info("Sending delete request %s", deletionURL)
        response = self.session.delete(deletionURL, verify=False)
        if response.status_code != requests.codes.ok and response.status_code != 204:
            raise DcmWebException(
                f"Error deleting study from {aet_rejection_stage} errorcode: {response.status_code} content {response.content}"
            )

        logger.info("Request Successfull, awaiting deletion to complete")
        time.sleep(5)
        for ae in [aet_rejection_stage, self.application_entity]:
            logger.info(f"Check if study is removed from {ae}")
            if self.get_instances_of_study(study_uid, ae):
                raise DcmWebException(f"Deletion of study {study_uid} failed")

        logger.info(f"Deletion of {study_uid} complete")

    def get_instances_of_study(self, study_uid, application_entity=None):
        """
        Get all instances of a study
        """
        application_entity = application_entity or self.application_entity
        url = f"{self.dcmweb_endpoint}/{application_entity}/rs/studies/{study_uid}/instances"
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
        url = f"{self.dcmweb_endpoint}/{self.application_entity}/rs/studies/{study_uid}/series/{series_uid}/instances"
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
        url = f"{self.dcmweb_endpoint}/{self.application_entity}/rs/studies/{study_uid}/series"
        r = self.session.get(url)
        if r.status_code == 204:
            return []
        elif r.status_code == 404:
            return None
        else:
            r.raise_for_status()
            return r.json()

    def delete_series(self, study_uid: str, series_uids: List[str]):
        logger.info(f"Deleting series {series_uids} in study {study_uid}")
        series = self.get_series_of_study(study_uid)
        series_uids_keep = [s["0020000E"]["Value"][0] for s in series]

        logger.warning(f"{series_uids_keep=}")
        logger.warning(f"{series_uids=}")

        for series_uid in series_uids:
            if series_uid not in series_uids_keep:
                logger.warn(
                    f"Series {series_uid} does not exist for study {study_uid} on PACS",
                )
                continue
            series_uids_keep.remove(series_uid)

        with tempfile.TemporaryDirectory() as tmp_dir:
            logger.info(f"1/4 Start Downloading all series to keep to {tmp_dir}")
            for keep_series_uid in series_uids_keep:
                logger.info(f"Downloading Series {keep_series_uid} to {tmp_dir}")
                if not self.downloadSeries(
                    keep_series_uid, tmp_dir, include_series_dir=True
                ):
                    raise DcmWebException(f"Could not download {keep_series_uid}")
                logger.info("Done")
            logger.info(f"Downloaded all series to keep to {tmp_dir}")

            logger.info(f"2/4 Delete complete study from pacs {tmp_dir}")
            self.delete_study(study_uid)
            logger.info("Study deleted")

            logger.info("3/4 Upload series to keep again to PACS")
            for upload_series_uid in series_uids_keep:
                logger.info(f"Upload series {upload_series_uid}")
                self.upload_dcm_files(os.path.join(tmp_dir, upload_series_uid))

            logger.info("4/4 Delete temp files")
            # deletion of tmp_files should happen automaticaly if scope of tmp_dir is left

        if self.get_instances_of_series(study_uid, series_uid):
            raise DcmWebException(f"Series {series_uid} still exists after deletion")
        logger.info(f"Series {series_uid} sucessfully deleted")

    def upload_dcm_files(self, path: str):
        files = glob(os.path.join(path, "*.dcm"))
        total_files = len(files)
        uploaded_fiels = 0
        for file in files:
            uploaded_fiels += 1
            logger.info("Uploading %d / %d:  %s", uploaded_fiels, total_files, file)
            dataset = pydicom.dcmread(file)
            self.client.store_instances(datasets=[dataset])

    def search_for_series(self, search_filters):
        return self.client.search_for_series(search_filters=search_filters)
