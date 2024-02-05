from pathlib import Path
import requests
import logging
import os
from google.auth.transport import requests
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


class DcmWebException(Exception):
    pass


class HelperGcloudDcmWeb:
    """
    Helper class for making authorized requests against a Google Healthcare API Dicom Store archive.
    """

    def __init__(self, application_entity: str, dag_run=None):
        """
        :param application_entity: Title of the application entity to communicate with
        :param dag_run: Airflow dag object.
        """
        self.application_entity = application_entity
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/kaapana/mounted/workflows/dags/credentials.json"

        assert dag_run

        # TODO Set google cloud authorization headers !!!
        # self.auth_headers = {
        #     "Authorization": f"Bearer {self.access_token}",
        #     "x-forwarded-access-token": self.access_token,
        # }

        # TODO Initialize DicomWeb client for once

    def get_session(self):
        credentials = service_account.Credentials.from_service_account_file(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        )
        scoped_credentials = credentials.with_scopes(
            ["https://www.googleapis.com/auth/cloud-platform"]
        )
        session = requests.AuthorizedSession(scoped_credentials)
        return session

    def get_instances_of_series(self, dicomweb_endpoint, series_uid, session):
        series_path = f"{dicomweb_endpoint}/instances"
        headers = {"Content-Type": "application/dicom+json; charset=utf-8"}
        response = session.get(series_path, params={
                               "SeriesInstanceUID": series_uid}, headers=headers)
        if not response.ok:
            print("################################")
            print("#")
            print("# Can't request series objects from PACS!")
            print(f"# UID: {series_uid}")
            print(f"# Status code: {response.status_code}")
            print("#")
            print("################################")
            return None

        return [[instance["0020000D"]["Value"][0],  # StudyInstanceUID
                 instance["0020000E"]["Value"][0],  # SeriesInstanceUID
                 instance["00080018"]["Value"][0]]  # SOPInstanceUID
                for instance in response.json()]

    def downloadSeries(self,
                       series_uid,
                       target_dir,
                       include_series_dir=False):

        session = self.get_session()
        dicomweb_endpoint = "https://healthcare.googleapis.com/v1/projects/idc-external-031/locations/europe-west2/datasets/kaapana-integration-test/dicomStores/kaapana-integration-test-store/dicomWeb"
        instance_list = self.get_instances_of_series(
            dicomweb_endpoint, series_uid, session
        )
        if instance_list is None:
            return False

        target_dir = Path(target_dir)
        if include_series_dir:
            target_dir = target_dir / series_uid
            target_dir.mkdir(parents=True, exist_ok=True)

        success = True
        for instance in instance_list:
            study_uid = instance[0]
            series_uid = instance[1]
            instance_uid = instance[2]
            result = self.download_instance(
                study_uid, series_uid, instance_uid, target_dir, dicomweb_endpoint, session)
            success &= result

        return success

    def download_instance(self,
                          study_uid,
                          series_uid,
                          instance_uid,
                          target_dir,
                          dicomweb_endpoint,
                          session
                          ):
        dicomweb_path = f"{dicomweb_endpoint}/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}"
        file_name = instance_uid + ".dcm"
        file_path = target_dir / file_name

        # Set the required Accept header on the request
        headers = {"Accept": "application/dicom; transfer-syntax=*"}
        response = session.get(dicomweb_path, headers=headers)

        if response.status_code != 200:
            print(f"Download of requested objectUID was not successful!\n"
                  f"seriesUID: {series_uid}\n"
                  f"studyUID: {study_uid}\n"
                  f"objectUID: {instance_uid}\n"
                  f"Status code: {response.status_code}\n"
                  f"Response content: {response.content}")
            return False

        try:
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(
                f"Retrieved DICOM instance and saved to {file_path} in current directory")
            return True
        except IOError as e:
            print(f"Failed to write file to {file_path}: {str(e)}")
            return False
