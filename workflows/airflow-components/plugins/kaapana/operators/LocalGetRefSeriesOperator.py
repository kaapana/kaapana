from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalGetRefSeriesOperator(KaapanaPythonBaseOperator):

    def downloadObject(self, studyUID, seriesUID, objectUID, downloadDir):
        import requests
        import os
        global client
        payload = {'requestType': 'WADO', 'studyUID': studyUID, 'seriesUID': seriesUID,
                   'objectUID': objectUID, 'contentType': 'application/dicom'}
        url = self.pacs_dcmweb + "/wado"
        response = requests.get(url, params=payload)

        fileName = objectUID+".dcm"

        filePath = os.path.join(downloadDir, fileName)

        print("Writing file {0} to {1} ...".format(fileName, downloadDir))
        with open(filePath, "wb") as f:
            f.write(response.content)

        return filePath

    def downloadSeries(self, studyUID, seriesUID, target_dir):
        import requests
        global client

        print("Downloading Series: %s" % seriesUID)
        print("Target DIR: %s" % target_dir)

        payload = {'StudyInstanceUID': studyUID,
                   'SeriesInstanceUID': seriesUID}
        url = self.pacs_dcmweb + "/rs/instances"
        httpResponse = requests.get(url, params=payload)
        print(payload)
        print(httpResponse)
        status = ""
        if httpResponse.status_code == 204:
            print("No results from pacs...")
        elif httpResponse.status_code == 200:
            status = "ok"
            response = httpResponse.json()
            print("Collecting objects for series {0}".format(seriesUID))
            objectUIDList = []
            for resultObject in response:
                objectUIDList.append(resultObject["00080018"]["Value"][0])  # objectUID

            print("Start downloading series: {0}".format(seriesUID))

            for objectUID in objectUIDList:
                self.downloadObject(studyUID, seriesUID, objectUID, target_dir)
        else:
            print("Error at PACS request!")
            status = "failed"
        return status

    def get_files(self, ds, **kwargs):
        from dicomweb_client.api import DICOMwebClient
        import pydicom
        import os
        import time
        import glob

        global client

        client = DICOMwebClient(
            url=self.pacs_dcmweb, qido_url_prefix="rs", wado_url_prefix="rs", stow_url_prefix="rs"
        )

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

        print("Starting module GetRefSeiresPETCTOperator")

        dcm_to_get_list = []
        for batch_element_dir in batch_folder:
            dcm_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"), recursive=True))
            if len(dcm_files) > 0:
                incoming_dcm = pydicom.dcmread(dcm_files[0])
                # print(incoming_dcm)
                if self.from_to == 'ptct':
                    dcm_to_get_list.append({
                        'study_id': incoming_dcm.StudyInstanceUID,
                        'series_uid': incoming_dcm.SeriesInstanceUID,
                        'related_series_uid': incoming_dcm.RelatedSeriesSequence[0].SeriesInstanceUID,
                        'target_dir': os.path.join(batch_element_dir, self.operator_out_dir)
                    })
                elif self.from_to == 'ptct-by-patient':
                    name = str(incoming_dcm["00100010"].value).replace("_PET", "_CT")
                    print("Search CT for patient: {}".format(name))
                    ct_series = client.search_for_series(search_filters={'00100010': name, '00080060': 'CT'})
                    dcm_to_get_list.append({
                        'study_id': ct_series[0]['0020000D']['Value'][0],
                        'series_uid': ct_series[0]['0020000E']['Value'][0],
                        'related_series_uid': ct_series[0]['0020000E']['Value'][0],
                        'target_dir': os.path.join(batch_element_dir, self.operator_out_dir)
                    })
                elif self.from_to == 'ptct-by-study':
                    ct_series = client.search_for_series(search_filters={'0020000D': incoming_dcm.StudyInstanceUID, '00080060': 'CT'})
                    dcm_to_get_list.append({
                        'study_id': incoming_dcm.StudyInstanceUID,
                        'series_uid': incoming_dcm.SeriesInstanceUID,
                        'related_series_uid': ct_series[0]['0020000E']['Value'][0],
                        'target_dir': os.path.join(batch_element_dir, self.operator_out_dir)
                    })
                elif self.from_to == 'segct':
                    referencedSeriesSequence = incoming_dcm[0x0008, 0x1115]
                    dcm_to_get_list.append({
                        'study_id': incoming_dcm[0x0020, 0x000D].value,
                        'series_uid': incoming_dcm[0x0020, 0x000e].value,
                        'related_series_uid': referencedSeriesSequence.value._list[0].SeriesInstanceUID,
                        'target_dir': os.path.join(batch_element_dir, self.operator_out_dir)
                    })

        # Download corresponding CTs:

        for dcm_to_get in dcm_to_get_list:
            if not os.path.exists(dcm_to_get['target_dir']):
                os.makedirs(dcm_to_get['target_dir'])
            status = self.downloadSeries(studyUID=dcm_to_get['study_id'], seriesUID=dcm_to_get['related_series_uid'], target_dir=dcm_to_get['target_dir'])
            if status == "failed":
                print("Could not download series...")
                exit(1)

    def __init__(self,
                 dag,
                 from_to,
                 pacs_dcmweb_host='http://dcm4chee-service.store.svc',
                 pacs_dcmweb_port='8080',
                 aetitle="KAAPANA",
                 *args, **kwargs):

        self.from_to = from_to
        self.pacs_dcmweb = pacs_dcmweb_host+":"+pacs_dcmweb_port + "/dcm4chee-arc/aets/"+aetitle.upper()

        super().__init__(
            dag,
            name='get-ref-series',
            python_callable=self.get_files,
            *args, **kwargs
        )
