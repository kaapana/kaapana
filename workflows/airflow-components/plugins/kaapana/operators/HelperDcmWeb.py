import requests
import os
from os.path import join
from pathlib import Path


class HelperDcmWeb():
    pacs_dcmweb_endpoint = "http://dcm4chee-service.store.svc:8080/dcm4chee-arc/aets/"
    pacs_dcmweb = pacs_dcmweb_endpoint + "KAAPANA"

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
        print(f"# Collecting objects for series {seriesUID}")
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

            print(("Start downloading series: {0}".format(seriesUID)))
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
    def qidoRs(aet, studyUID, seriesUID=None):
        """
        Quido a study or series.
        :param aet: The AETitle of the requested resource.
        :type studyUID: String
        :param studyUID: The UID of the study to reject.
        :type studyUID: String
        :param seriesUID: The UID of the study to reject.
        :type seriesUID: String or None
        :returns: requests.Response
        """
        if seriesUID:
            return requests.get("{}{}/rs/studies/{}/series/{}/instances"
                                .format(HelperDcmWeb.pacs_dcmweb_endpoint, aet, studyUID, seriesUID), verify=False)
        return requests.get("{}{}/rs/studies/{}/instances"
                            .format(HelperDcmWeb.pacs_dcmweb_endpoint, aet, studyUID), verify=False)


    @staticmethod
    def rejectDicoms(studyUID, seriesUID=None):
        """
        Rejects a study or a series to IOM_QUALITY
        :param studyUID: The UID of the study to reject.
        :type studyUID: String
        :param seriesUID: The UID of the study to reject.
        :type seriesUID: String
        :returns: requests.Response
        """
        if seriesUID:
            rejectUrl = "{}/rs/studies/{}/series/{}/reject/113001%5EDCM".format(HelperDcmWeb.pacs_dcmweb, studyUID,
                                                                                seriesUID)
        else:
            rejectUrl = "{}/rs/studies/{}/reject/113001%5EDCM".format(HelperDcmWeb.pacs_dcmweb, studyUID)

        return requests.post(rejectUrl, verify=False)

    @staticmethod
    def deleteStudy(rejectedStudyUID):
        """
        Delete a study from IOM_QUALITY. It has to be added to IOM_QAULITY frist (by rejectSeries)
        :param studyUID: The UID of the study to reject.
        :type studyUID: String
        :param seriesUID: The UID of the study to reject.
        :type seriesUID: String
        :returns: requests.Response
        """
        reject_url = "{}IOCM_QUALITY/rs/studies/{}".format(HelperDcmWeb.pacs_dcmweb_endpoint, rejectedStudyUID)
        return requests.delete(reject_url, verify=False)

