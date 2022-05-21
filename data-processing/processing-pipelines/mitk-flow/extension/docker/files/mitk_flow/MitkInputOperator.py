from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
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

        return fileName

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
        file_names = []
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
            file_name_list = []
            for objectUID in objectUIDList:
                file_name_list.append(self.downloadObject(studyUID, seriesUID,
                                                          objectUID, target_dir))

        else:
            print("Error at PACS request!")
            status = "failed"
        return status, file_name_list

    def createScene(self, mitk_scenes):
        print("Creating MITK scene file!")
        for element in mitk_scenes:

            node = ElementTree.Element("node", UID="Node_1")
            ElementTree.SubElement(node, "data", {'type': "Image", 'file': element['file_image']})
            ElementTree.SubElement(node, "properties", file="image_props")
            start_tree = ElementTree.ElementTree(node)
            # add image name, to prevent auto-created segmentation with e.g. / in seg name
            output_file = os.path.join(element['scene_dir'], "image_props")
            image_name = ElementTree.Element("property", {'key': "name", 'type': "StringProperty"})
            ElementTree.SubElement(image_name, "string", value=element['image_seriesUID'])
            image_layer = ElementTree.Element("property", {'key': "layer", 'type': "IntProperty"})
            ElementTree.SubElement(image_layer, "int", value="0")

            start_prop = ElementTree.ElementTree(image_name)
            print('Writing image_props')
            start_prop.write(output_file, xml_declaration=True, encoding='utf-8', method="xml")

            xmlstr = ElementTree.tostring(image_layer, encoding='utf-8', method="xml").decode()
            print('Writing layer property to property file')
            with open(output_file, "a") as myfile:
                myfile.write(xmlstr)

            output_file = os.path.join(element['scene_dir'], "input.mitksceneindex")
            print('Writing scene file')
            start_tree.write(output_file, xml_declaration=True, encoding='utf-8', method="xml")

            if element['hasSegementation']:
                node2 = ElementTree.Element("node", UID="Node_2")
                ElementTree.SubElement(node2, "source", UID="Node_1")
                data = ElementTree.Element("data", {'type': "LabelSetImage", 'file': element['file_seg']})
                ElementTree.SubElement(data, "properties", file="segmetation_data_props")
                node2.append(data)
                ElementTree.SubElement(node2, "properties", file="segmetation_props")
                xmlstr = ElementTree.tostring(node2, encoding='utf-8', method="xml").decode()
                print('Writing Segmentation node to scene file')
                with open(output_file, "a") as myfile:
                    myfile.write(xmlstr)

                output_file = os.path.join(element['scene_dir'], "segmetation_props")
                seg_name = ElementTree.Element("property", {'key': "name", 'type': "StringProperty"})
                ElementTree.SubElement(seg_name, "string", value="Segmentation")
                seg_layer = ElementTree.Element("property", {'key': "layer", 'type': "IntProperty"})
                ElementTree.SubElement(seg_layer, "int", value="1")
                start_prop = ElementTree.ElementTree(seg_name)

                print('Writing segmetation_props')
                start_prop.write(output_file, xml_declaration=True, encoding='utf-8', method="xml")

                xmlstr = ElementTree.tostring(seg_layer, encoding='utf-8', method="xml").decode()
                print('Writing layer property to property file')
                with open(output_file, "a") as myfile:
                    myfile.write(xmlstr)
                # Setting the referenceFile is a workaround, because of limitations saving existing dicm-seg objects
                # https://phabricator.mitk.org/T26953
                output_file = os.path.join(element['scene_dir'], "segmetation_data_props")
                property = ElementTree.Element("property",
                                               {'key': "referenceFiles", 'type': "StringLookupTableProperty"})
                string_lookup_table = ElementTree.Element("StringLookupTable")
                # Setting absolut path
                # It has to have an index, first tests show that the index number must not match the dcm index
                # TODO: this has to be verified

                for idx, file in enumerate(element['file_image_container_list']):
                    ElementTree.SubElement(string_lookup_table, "LUTValue", id=str(idx), value=os.path.join("/", file))
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
                seriesUID = incoming_dcm.SeriesInstanceUID

                # check if it is a segmentation, if so, download the referencing images
                if "ReferencedSeriesSequence" in incoming_dcm:
                    reference = incoming_dcm.ReferencedSeriesSequence
                    seriesUID = reference._list[0].SeriesInstanceUID
                    REF_IMG = 'REF_IMG'
                    target_dir = os.path.join(batch_element_dir, REF_IMG)
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir)

                    status, file_names = self.downloadSeries(studyUID=incoming_dcm.StudyInstanceUID,
                                                             seriesUID=seriesUID,
                                                             target_dir=target_dir)
                    data_path_list = []
                    for file_name in file_names:
                        data_path_list.append(
                            os.path.join("/", WORKFLOW_DIR, BATCH_NAME, path_dir, REF_IMG, file_name))
                    if status == 'ok':
                        mitk_scenes.append({
                            'hasSegementation': True,
                            'file_image': os.path.join(REF_IMG, file_names[0]),
                            'file_seg': os.path.join(self.operator_in_dir, os.path.basename(dcm_files[0])),
                            'scene_dir': batch_element_dir,
                            'file_image_container_list': data_path_list,
                            'image_seriesUID' : seriesUID
                        })
                    else:
                        print('Reference images to segmentation not found!')
                        raise ValueError('ERROR')
                # otherwise only open images without segmentation
                else:
                    print("No segementaion, create scene with image only")
                    mitk_scenes.append({
                        'hasSegementation': False,
                        'file_image': os.path.join(self.operator_in_dir, os.path.basename(dcm_files[0])),
                        'file_seg': None,
                        'scene_dir': batch_element_dir,
                        'image_seriesUID' : seriesUID
                    })
            self.createScene(mitk_scenes)

    def __init__(self,
                 dag,
                 pacs_dcmweb_host='http://dcm4chee-service.store.svc',
                 pacs_dcmweb_port='8080',
                 aetitle="KAAPANA",
                 **kwargs):

        self.pacs_dcmweb = pacs_dcmweb_host + ":" + pacs_dcmweb_port + "/dcm4chee-arc/aets/" + aetitle.upper()

        super().__init__(
            dag=dag,
            name='get-mitk-input',
            python_callable=self.get_files,
            **kwargs
        )