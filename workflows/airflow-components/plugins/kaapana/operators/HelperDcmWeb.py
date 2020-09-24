import requests
import os

class HelperDcmWeb():
    pacs_dcmweb = "http://dcm4chee-service.store.svc:8080/dcm4chee-arc/aets/KAAPANA"

    @staticmethod
    def downloadSeries(studyUID, seriesUID, dag_run_id, target_dir):
        payload = {'StudyInstanceUID': studyUID,
                   'SeriesInstanceUID': seriesUID}
        url = HelperDcmWeb.pacs_dcmweb + "/rs/instances"
        httpResponse = requests.get(url, params=payload)
        print(payload)
        print(httpResponse)
        if httpResponse.status_code == 204:
            print("No results from pacs...")
            print("Can't request series!")
            exit(1)
        elif httpResponse.status_code == 200:
            response = httpResponse.json()
            print(("Collecting objects for series {0}".format(seriesUID)))
            objectUIDList = []
            for resultObject in response:
                objectUIDList.append(
                    resultObject["00080018"]["Value"][0])  # objectUID

            print(("Start downloading series: {0}".format(seriesUID)))
            for objectUID in objectUIDList:
                HelperDcmWeb.downloadObject(
                    studyUID=studyUID, seriesUID=seriesUID, objectUID=objectUID, downloadDir=target_dir)
            print("Done.")
        else:
            print("Error at PACS request!")
            exit(1)

    @staticmethod
    def downloadObject(studyUID, seriesUID, objectUID, downloadDir):
        payload = {'requestType': 'WADO', 'studyUID': studyUID, 'seriesUID': seriesUID,
                   'objectUID': objectUID, 'contentType': 'application/dicom'}
        url = HelperDcmWeb.pacs_dcmweb + "/wado"
        response = requests.get(url, params=payload)
        fileName = objectUID+".dcm"
        filePath = os.path.join(downloadDir, fileName)
        with open(filePath, "wb") as f:
            f.write(response.content)

