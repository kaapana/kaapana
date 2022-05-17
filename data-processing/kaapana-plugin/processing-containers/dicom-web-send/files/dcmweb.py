import requests
import os
import uuid
from dicomweb_client.api import DICOMwebClient
import pydicom
import glob


def downloadObject(studyUID, seriesUID, objectUID, downloadDir):
    global client
    payload = {
        'requestType': 'WADO',
        'studyUID': studyUID,
        'seriesUID': seriesUID,
        'objectUID': objectUID,
        'contentType': 'application/dicom'
    }
    url = pacsURL + "/wado"
    response = requests.get(url, params=payload)
    fileName = objectUID+".dcm"
    filePath = os.path.join(downloadDir, fileName)
    print("Writing file {0} to {1} ...".format(fileName, downloadDir))
    with open(filePath, "wb") as f:
        f.write(response.content)

    return filePath


def downloadSeries(studyUID, seriesUID, baseDir):
    global client

    uuidFolder = str(uuid.uuid4())
    downloadDir = os.path.join(baseDir, uuidFolder)
    os.mkdir(downloadDir)

    payload = {
        'StudyInstanceUID': studyUID,
        'SeriesInstanceUID': seriesUID
    }
    url = pacsURL + "/rs/instances"
    httpResponse = requests.get(url, params=payload)
    print(payload)
    print(httpResponse)
    response = httpResponse.json()

    print("Collecting objects for series {0}".format(seriesUID))
    objectUIDList = []
    for resultObject in response:
        objectUIDList.append(resultObject["00080018"]["Value"][0])  # objectUID

    print("Start downloading series: {0}".format(seriesUID))

    for objectUID in objectUIDList:
        downloadObject(studyUID, seriesUID, objectUID, downloadDir)

    return downloadDir


def uploadDicomObject(pathToFile):
    global client
    ds = pydicom.dcmread(pathToFile)
    studyInstanceUID = str(ds[0x0020, 0x000D].value)

    client.store_instances([ds], studyInstanceUID)
    return


def init(pacs_origin, port, aetitle):
    global client

    pacsURL = pacs_origin+":"+port+"/dcm4chee-arc/aets/"+aetitle.upper()

    client = DICOMwebClient(
        url=pacsURL, qido_url_prefix="rs", wado_url_prefix="rs", stow_url_prefix="rs"
    )


if __name__ == "__main__":

    print("DICOMweb send started..")

    batch_input_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])

    file_list = sorted(glob.glob(os.path.join(batch_input_dir, "**/*.dcm*"), recursive=True))

    # todo, check if also runs with multiple images...
    batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

    for batch_element_dir in batch_folders:

        element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
        file_list += sorted(glob.glob(os.path.join(element_input_dir, "**/*.dcm*"), recursive=True))

    file_list = sorted(file_list)

    pacs_origin = os.getenv("PACS_ORIGIN", None)
    port = os.getenv("PORT", None)
    aetitle = os.getenv("AETITLE", None)
    init(pacs_origin=pacs_origin, port=port, aetitle=aetitle)
    # file_list = glob.glob(input_dir+"/*/*.dcm")

    file_count = 0
    for dcm_file in file_list:
        print("Found file: %s" % dcm_file)
        file_count += 1
        print("Sending file: %s" % dcm_file)
        uploadDicomObject(dcm_file)

    if file_count == 0:
        print("No corresponding dcm file found!")
        exit(1)
    else:
        print("DICOMweb send done.")
        exit(0)
