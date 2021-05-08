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
from urllib3.filepost import encode_multipart_formdata, choose_boundary


class DcmWebException(Exception):
    pass

class HelperDcmWeb():
    pacs_dcmweb_endpoint = "http://dcm4chee-service.store.svc:8080/dcm4chee-arc/aets/"
    #pacs_dcmweb_endpoint = "http://10.128.128.212:8080/dcm4chee-arc/aets/"
    pacs_dcmweb = pacs_dcmweb_endpoint + "KAAPANA"
    client = DICOMwebClient(url=f"{pacs_dcmweb}/rs")
    wait_time=5
    log = logging.getLogger(__name__)

    @staticmethod
    def checkIfSeriesAvailable(seriesUID):
        payload = {
            'SeriesInstanceUID': seriesUID
        }
        url = HelperDcmWeb.pacs_dcmweb + "/rs/instances"
        httpResponse = requests.get(url, params=payload)
        if httpResponse.status_code == 200:
            return True
        else:
            return False
    
    @staticmethod
    def downloadSeries(seriesUID, target_dir, include_series_dir=False):
        payload = {
            'SeriesInstanceUID': seriesUID
        }
        url = HelperDcmWeb.pacs_dcmweb + "/rs/instances"
        httpResponse = requests.get(url, params=payload)
        # print(f"Requesting URL: {url}")
        # print(f"httpResponse: {httpResponse}")
        # print(f"payload: {payload}")
        if httpResponse.status_code == 200:
            response = httpResponse.json()
            objectUIDList = []
            for resultObject in response:
                objectUIDList.append(
                    [
                        resultObject["0020000D"]["Value"][0],
                        resultObject["00080018"]["Value"][0]
                    ]
                )  # objectUID

            if include_series_dir:
                target_dir = join(target_dir, seriesUID)
            Path(target_dir).mkdir(parents=True, exist_ok=True)
            for objectUID in objectUIDList:
                studyUID = objectUID[0]
                objectUID = objectUID[1]
                HelperDcmWeb.downloadObject(
                    studyUID=studyUID,
                    seriesUID=seriesUID,
                    objectUID=objectUID,
                    target_dir=target_dir
                )
            return True
        else:
            print("################################")
            print("#")
            print("# Can't request series objects from PACS!")
            print(f"# UID: {seriesUID}")
            print(f"# Status code: {httpResponse.status_code}")
            print("#")
            print("################################")
            return False

    @ staticmethod
    def downloadObject(studyUID, seriesUID, objectUID, target_dir):
        payload = {
            'requestType': 'WADO',
            'studyUID': studyUID,
            'seriesUID': seriesUID,
            'objectUID': objectUID,
            'contentType': 'application/dicom'
        }
        url = HelperDcmWeb.pacs_dcmweb + "/wado"
        response = requests.get(url, params=payload)
        fileName = objectUID+".dcm"
        filePath = os.path.join(target_dir, fileName)
        with open(filePath, "wb") as f:
            f.write(response.content)

    @staticmethod
    def quido_rs(aet: str, sub_url: str):
        """
        Search a study or series. via QUIDO-RS
        https://www.dicomstandard.org/dicomweb/query-qido-rs

        :returns: DICOM JSon or None if nothing found
        """
        url = f"{HelperDcmWeb.pacs_dcmweb_endpoint}{aet}/rs{sub_url}"

        response = requests.get(url,
                            #params={'Accept': 'application/json'},
                            verify=False)

        if response.status_code == requests.codes.ok:
            return response.json()
        elif response.status_code == 204:
            return None
        else:
            raise DcmWebException(f"Error accessing {url} errorcode {response.status_code}")

    @staticmethod
    def getStudy(aet: str, study_uid: str):
        return HelperDcmWeb.quido_rs(aet, f"/studies/{study_uid}/instances")

    @staticmethod
    def getSeries(aet: str, study_uid: str, series_uid: str):
        return HelperDcmWeb.quido_rs(aet, f"/studies/{study_uid}/series/{series_uid}/instances")

    @staticmethod
    def getSeriesUidsForStudy(aet: str, study_uid: str) -> List[str]:
        series = HelperDcmWeb.quido_rs(aet, f"/studies/{study_uid}/series")
        return [s["0020000E"]["Value"][0] for s in series] if series else []

    @staticmethod
    def delete_series(aet: str, study_uid: str, series_uids: List[str]):
        HelperDcmWeb.log.info("Deleting series %s in study %s", series_uids, study_uid)
        series_uids_keep = HelperDcmWeb.getSeriesUidsForStudy(aet, study_uid)

        for series_uid in series_uids:
            if series_uid not in series_uids_keep:
                HelperDcmWeb.log.warn("Series %s does not exist for study %s on PACS", series_uid, study_uid)
                return
            series_uids_keep.remove(series_uid)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            HelperDcmWeb.log.info("1/4 Start Downloading all series to keep to %s", tmp_dir)
            for keep_series_uid in series_uids_keep:
                HelperDcmWeb.log.info("Downloading Series %s to %s", keep_series_uid, tmp_dir)      
                if not HelperDcmWeb.downloadSeries(keep_series_uid, tmp_dir, include_series_dir=True):
                    raise DcmWebException(f"Could not download {keep_series_uid}")
                HelperDcmWeb.log.info("Done")
            HelperDcmWeb.log.info("Downloaded all series to keep to %s", tmp_dir)

            HelperDcmWeb.log.info("2/4 Delete complete study from pacs %s", tmp_dir)
            HelperDcmWeb.delete_study(aet, study_uid)
            HelperDcmWeb.log.info("Study deleted")

            HelperDcmWeb.log.info("3/4 Upload series to keep again to PACS")
            for upload_series_uid in series_uids_keep:
                HelperDcmWeb.log.info("Upload series %s", upload_series_uid)
                HelperDcmWeb.upload_dcm_files(aet, os.path.join(tmp_dir, upload_series_uid))

            HelperDcmWeb.log.info("4/4 Delete temp files")
            # deletion of tmp_files should happen automaticaly if scope of tmp_dir is left

        if HelperDcmWeb.getSeries(aet, study_uid, series_uid):
            raise DcmWebException(f"Series {series_uid} still exists after deletion")
        HelperDcmWeb.log.info("Series %s sucessfully deleted", series_uid)

    @staticmethod
    def upload_dcm_files(aet: str, path: str):
        files = glob(os.path.join(path, "*.dcm"))
        total_files = len(files)
        uploaded_fiels = 0
        for file in files:
            uploaded_fiels += 1
            HelperDcmWeb.log.info("Uploading %d / %d:  %s", uploaded_fiels, total_files, file)
            dataset = pydicom.dcmread(file)
            HelperDcmWeb.client.store_instances(datasets=[dataset])


    @staticmethod
    def delete_study(aet: str, study_uid: str):
        HelperDcmWeb.log.info("Deleting study %s", study_uid)
        if not HelperDcmWeb.getStudy(aet, study_uid):
            HelperDcmWeb.log.warn("Study does not exist on PACS")
            return
        
        HelperDcmWeb.log.info("1/2: rejecting study")
        rejectionURL = f"{HelperDcmWeb.pacs_dcmweb}/rs/studies/{study_uid}/reject/113001%5EDCM"
        response = requests.post(rejectionURL, verify=False)

        if response.status_code != requests.codes.ok and response.status_code != 204:
            raise DcmWebException(f"Rejection faild {rejectionURL}")
        HelperDcmWeb.log.info("Awaiting rejection to complete")
        time.sleep(HelperDcmWeb.wait_time)
        HelperDcmWeb.log.info("Rejection complete")
        # After the rejection there can be Key Object Selection Document Storage left on the pacs,
        # these will disapear when the study is finaly deleted, so a check HelperDcmWeb.getStudy(aet, study_uid)
        # may still return results in this spot

        HelperDcmWeb.log.info("2/2: deleting study")

        aet_rejection_stage = "IOCM_QUALITY"
        if not HelperDcmWeb.getStudy(aet_rejection_stage, study_uid):
            raise DcmWebException(f"Could not find study {study_uid} in aet {aet_rejection_stage}")
        HelperDcmWeb.log.info("Found study %s in aet %s", study_uid, study_uid)
        
        deletionURL = f"{HelperDcmWeb.pacs_dcmweb_endpoint}IOCM_QUALITY/rs/studies/{study_uid}"
        HelperDcmWeb.log.info("Sending delete request %s", deletionURL)
        response = requests.delete(deletionURL, verify=False)

        if response.status_code != requests.codes.ok and response.status_code != 204:
            raise DcmWebException("Error deleting study form iocm quality errorcode: %d content %s", response.status_code, response.content)

        HelperDcmWeb.log.info("Request Successfull, awaiting deletion to complete")
        time.sleep(HelperDcmWeb.wait_time)

        HelperDcmWeb.log.info("Check if study is removed from %s", aet_rejection_stage)
        if HelperDcmWeb.getStudy(aet_rejection_stage, study_uid):
            raise DcmWebException(f"Deletion of study {study_uid} faild")

        HelperDcmWeb.log.info("Check if study is removed from %s", aet)
        if HelperDcmWeb.getStudy(aet, study_uid):
            raise DcmWebException(f"Deletion of study {study_uid} faild")

        HelperDcmWeb.log.info("Deletion of %s complete", study_uid)


    @staticmethod
    def reject_series(aet: str, study_uid: str, series_uid: str):
        url = f"{HelperDcmWeb.pacs_dcmweb}/rs/studies/{study_uid}/series/{series_uid}/reject/113001%5EDCM"
        response = requests.post(url, verify=False)

        if response.status_code != requests.codes.ok and response.status_code != 204:
            raise DcmWebException(f"Rejection faild {url}")
        HelperDcmWeb.log.info("Awaiting rejection to complete")
        time.sleep(HelperDcmWeb.wait_time)

        if HelperDcmWeb.getSeries(aet, study_uid, series_uid):
            raise DcmWebException("Rejection Faild")

        HelperDcmWeb.log.info("Rejection complete")