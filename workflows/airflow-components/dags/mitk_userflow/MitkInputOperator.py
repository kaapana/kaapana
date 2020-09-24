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
        for element in mitk_scenes:

            node = ElementTree.Element("node", UID="Node_1")
            ElementTree.SubElement(node, "data", {'type': "Image", 'file': element['file_image']})
            ElementTree.SubElement(node, "properties", file="image_node_props")
            start_tree = ElementTree.ElementTree(node)
            output_file = os.path.join(element['scene_dir'], "input.mitksceneindex")
            print('Writing scene file')
            start_tree.write(output_file, xml_declaration=True, encoding='utf-8', method="xml")

            if element['hasSegementation']:
                node2 = ElementTree.Element("node", UID="Node_2")
                ElementTree.SubElement(node2, "source", UID="Node_1")
                ElementTree.SubElement(node2, "data", {'type': "LabelSetImage", 'file': element['file_seg']})
                ElementTree.SubElement(node2, "properties", file="segmetation_props")
                xmlstr = ElementTree.tostring(node2, encoding='utf-8', method="xml").decode()
                print('Writing Segmentation node to scene file')
                with open(output_file, "a") as myfile:
                    myfile.write(xmlstr)

            name_props = ElementTree.Element("property", {'key': "name", 'type': "StringProperty"})
            ElementTree.SubElement(name_props, "string", value="Input_images")
            opacity_props = ElementTree.Element("property", {'key': "opacity", 'type': "FloatProperty"})
            ElementTree.SubElement(opacity_props, "float", value="0.8")
            selected_props = ElementTree.Element("property", {'key': "selected", 'type': "BoolProperty"})
            ElementTree.SubElement(selected_props, "bool", value="false")
            start_prop = ElementTree.ElementTree(name_props)
            print('Writing image_node_props')
            output_file = os.path.join(element['scene_dir'], "image_node_props")
            start_prop.write(output_file, xml_declaration=True, encoding='utf-8', method="xml")
            opacity_str = ElementTree.tostring(opacity_props, encoding='utf-8', method="xml").decode()
            selected_str = ElementTree.tostring(selected_props, encoding='utf-8', method="xml").decode()
            with open(output_file, "a") as myfile:
                myfile.write(opacity_str)
                myfile.write(selected_str)

            if element['hasSegementation']:
                seg_props = list()
                seg_name = ElementTree.Element("property", {'key': "name", 'type': "StringProperty"})
                ElementTree.SubElement(seg_name, "string", value="Segmentation")
                seg_opacity = ElementTree.Element("property", {'key': "opacity", 'type': "FloatProperty"})
                ElementTree.SubElement(seg_opacity, "float", value="0.7")
                seg_props.append(seg_opacity)
                seg_typ = ElementTree.Element("property", {'key': "segmentation", 'type': "BoolProperty"})
                ElementTree.SubElement(seg_typ, "bool", value="true")
                seg_props.append(seg_typ)
                seg_selected = ElementTree.Element("property", {'key': "selected", 'type': "BoolProperty"})
                ElementTree.SubElement(seg_selected, "bool", value="true")
                seg_props.append(seg_selected)
                seg_binary = ElementTree.Element("property", {'key': "binary", 'type': "BoolProperty"})
                ElementTree.SubElement(seg_binary, "bool", value="true")
                seg_props.append(seg_binary)
                seg_color = ElementTree.Element("property", {'key': "color", 'type': "ColorProperty"})
                ElementTree.SubElement(seg_color, "color", {'r': "1", 'g': "0", 'b': "0"})
                seg_props.append(seg_color)

                start_prop = ElementTree.ElementTree(seg_name)
                print('Writing segmetation_props')
                output_file = os.path.join(element['scene_dir'], "segmetation_props")
                start_prop.write(output_file, xml_declaration=True, encoding='utf-8', method="xml")
                with open(output_file, "a") as myfile:
                    for prop in seg_props:
                        prop_str = ElementTree.tostring(prop, encoding='utf-8', method="xml").decode()
                        myfile.write(prop_str)

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
            dcm_files = sorted(
                glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"), recursive=True))
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
                            mitk_scenes.append({
                                'hasSegementation': True,
                                'file_image': os.path.join(REF_IMG, fileName),
                                'file_seg': os.path.join(INITIAL_INPUT_DIR, os.path.basename(dcm_files[0])),
                                'scene_dir': batch_element_dir
                            })
                        else:
                            print('Reference images to segmentation not found!')
                            exit(1)
                # otherwise only open images without segmentation
                else:
                    mitk_scenes.append({
                        'hasSegementation': False,
                        'file_image': os.path.join(INITIAL_INPUT_DIR, os.path.basename(dcm_files[0])),
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


