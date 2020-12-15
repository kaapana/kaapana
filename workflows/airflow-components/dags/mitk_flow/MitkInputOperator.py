from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR, INITIAL_INPUT_DIR
from xml.etree import ElementTree
import os


class MitkInputOperator(KaapanaPythonBaseOperator):

    def downloadObject(self, studyUID, seriesUID, objectUID, downloadDir):
        import requests
        global client
        payload = {'requestType': 'WADO', 'studyUID': studyUID, 'seriesUID': seriesUID,
                   'objectUID': objectUID, 'contentType': 'application/dicom'}
        url = self.pacs_dcmweb + "/wado"
        response = requests.get(url, params=payload)

        fileName = objectUID + ".dcm"

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
        fileName = ""
        if httpResponse.status_code == 204:
            print("No results from pacs...")
        elif httpResponse.status_code == 200:
            status = "ok"
            response = httpResponse.json()
            print("Collecting objects for series {0}".format(seriesUID))
            objectUIDList = []
            for resultObject in response:
                objectUIDList.append(
                    resultObject["00080018"]["Value"][0])  # objectUID

            print("Start downloading series: {0}".format(seriesUID))

            for objectUID in objectUIDList:
                self.downloadObject(studyUID, seriesUID,
                                    objectUID, target_dir)
            if objectUIDList[0]:
                fileName = objectUIDList[0] + ".dcm"
        else:
            print("Error at PACS request!")
            status = "failed"
        return status, fileName

    def createScene(self, mitk_scenes):
        print("Creating MITK scene file!")
        for element in mitk_scenes:

            node = ElementTree.Element("node", UID="Node_1")
            ElementTree.SubElement(node, "data", {'type': "Image", 'file': element['file_image']})
            start_tree = ElementTree.ElementTree(node)
            output_file = os.path.join(element['scene_dir'], "input.mitksceneindex")
            print('Writing scene file')
            start_tree.write(output_file, xml_declaration=True, encoding='utf-8', method="xml")

            if element['hasSegementation']:
                node2 = ElementTree.Element("node", UID="Node_2")
                ElementTree.SubElement(node2, "source", UID="Node_1")
                data = ElementTree.Element("data", {'type': "LabelSetImage", 'file': element['file_seg']})
                ElementTree.SubElement(data,  "properties", file="segmetation_data_props")
                node2.append(data)
                ElementTree.SubElement(node2, "properties", file="segmetation_props")
                xmlstr = ElementTree.tostring(node2, encoding='utf-8', method="xml").decode()
                print('Writing Segmentation node to scene file')
                with open(output_file, "a") as myfile:
                    myfile.write(xmlstr)

                output_file = os.path.join(element['scene_dir'], "segmetation_props")
                seg_name = ElementTree.Element("property", {'key': "name", 'type': "StringProperty"})
                ElementTree.SubElement(seg_name, "string", value="Segmentation")
                start_prop = ElementTree.ElementTree(seg_name)
                print('Writing segmetation_props')
                start_prop.write(output_file, xml_declaration=True, encoding='utf-8', method="xml")

                # Setting the referenceFile is a workaround, because of limitations saving existing dicm-seg objects
                # https://phabricator.mitk.org/T26953
                output_file = os.path.join(element['scene_dir'], "segmetation_data_props")
                property = ElementTree.Element("property", {'key': "referenceFiles", 'type': "StringLookupTableProperty"})
                string_lookup_table = ElementTree.Element("StringLookupTable")
                file_path = element['file_image_absolute_container']
                ElementTree.SubElement(string_lookup_table,
                                       "LUTValue",
                                       value= element['file_image_absolute_container'])
                property.append(string_lookup_table)
                segmetation_data_props = ElementTree.ElementTree(property)
                print('Writing segmetation_data_props')
                segmetation_data_props.write(output_file, xml_declaration=True, encoding='utf-8', method="xml")



    def get_files(self, ds, **kwargs):
        from dicomweb_client.api import DICOMwebClient
        import pydicom
        import time
        import glob

        global client

        client = DICOMwebClient(
            url=self.pacs_dcmweb, qido_url_prefix="rs", wado_url_prefix="rs", stow_url_prefix="rs"
        )

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]


        print("Starting module MtikInputOperator")
    
        mitk_scenes = []
        for batch_element_dir in batch_folder:
            print("batch_element_dir: " + batch_element_dir)
            path_dir = os.path.basename(batch_element_dir)
            print("oerator_in_dir: ", self.operator_in_dir)
            dcm_files = sorted(
                glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"), recursive=True))
            print("Dicmo flies: ", dcm_files)
            if len(dcm_files) > 0:
                incoming_dcm = pydicom.dcmread(dcm_files[0])

                # check if it is a segmentation, if so, download the referencing images
                if "ReferencedSeriesSequence" in incoming_dcm:
                    reference = incoming_dcm.ReferencedSeriesSequence
                    seriesUID = reference._list[0].SeriesInstanceUID
                    REF_IMG = 'REF_IMG'
                    target_dir = os.path.join(batch_element_dir, REF_IMG)
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir)

                        status, fileName = self.downloadSeries(studyUID=incoming_dcm.StudyInstanceUID,
                                                               seriesUID=seriesUID,
                                                               target_dir=target_dir)
                        if status == 'ok':
                            data_path = os.path.join(WORKFLOW_DIR, BATCH_NAME, path_dir, REF_IMG, fileName )
                            abs_container_path = "/" + data_path
                            mitk_scenes.append({
                                'hasSegementation': True,
                                'file_image': os.path.join(REF_IMG, fileName),
                                'file_seg': os.path.join(self.operator_in_dir, os.path.basename(dcm_files[0])),
                                'scene_dir': batch_element_dir,
                                'file_image_absolute_container' : abs_container_path
                            })
                        else:
                            print('Reference images to segmentation not found!')
                            exit(1)
                # otherwise only open images without segmentation
                else:
                    print("No segementaion, create scene with image only")
                    mitk_scenes.append({
                        'hasSegementation': False,
                        'file_image': os.path.join(self.operator_in_dir, os.path.basename(dcm_files[0])),
                        'file_seg': None,
                        'scene_dir': batch_element_dir
                    })
            self.createScene(mitk_scenes)

    def __init__(self,
                 dag,
                 parallel_id=None,
                 pacs_dcmweb_host='http://dcm4chee-service.store.svc',
                 pacs_dcmweb_port='8080',
                 aetitle="KAAPANA",
                 *args, **kwargs):

        self.pacs_dcmweb = pacs_dcmweb_host + ":" + pacs_dcmweb_port + "/dcm4chee-arc/aets/" + aetitle.upper()

        # parallel_id=from_to

        super().__init__(
            dag,
            name='get-mitk-input',
            python_callable=self.get_files,
            *args, **kwargs
            # parallel_id=parallel_id,
        )


