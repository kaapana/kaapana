import json
import os
import shutil
import time
import requests
import glob
from pathlib import Path
from typing import List, Dict
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_utils import get_release_name
from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from xml.etree import ElementTree
from kaapana.blueprints.kaapana_global_variables import (
    PROCESSING_WORKFLOW_DIR,
    ADMIN_NAMESPACE,
    SERVICES_NAMESPACE,
    JOBS_NAMESPACE,
)


class LocalCreateMITKScene(KaapanaPythonBaseOperator):
    def createScene(self, mitk_scenes, batch_element_dir):
        print("Creating MITK scene file!")
        output_dir = batch_element_dir
        output_file = os.path.join(output_dir, "input.mitksceneindex")

        for index, element in enumerate(mitk_scenes):
            uid = "Node_" + str(index)
            node = ElementTree.Element("node", UID=uid)

            ElementTree.SubElement(
                node, "data", {"type": "Image", "file": element["file_image"]}
            )
            ElementTree.SubElement(node, "properties", file="image_props_" + str(index))

            if index == 0:
                start_tree = ElementTree.ElementTree(node)
                start_tree.write(
                    output_file, xml_declaration=True, encoding="utf-8", method="xml"
                )
                print("Writing scene file")
            else:
                xmlstr = ElementTree.tostring(
                    node, encoding="utf-8", method="xml"
                ).decode()
                with open(output_file, "a") as myfile:
                    myfile.write(xmlstr)

            image_prop_file = os.path.join(output_dir, "image_props_" + str(index))

            image_name = ElementTree.Element(
                "property", {"key": "name", "type": "StringProperty"}
            )
            ElementTree.SubElement(image_name, "string", value=element["image_name"])

            image_layer = ElementTree.Element(
                "property", {"key": "layer", "type": "IntProperty"}
            )
            ElementTree.SubElement(image_layer, "int", value=str(index))

            start_prop = ElementTree.ElementTree(image_name)
            start_prop.write(
                image_prop_file, xml_declaration=True, encoding="utf-8", method="xml"
            )

            xmlstr = ElementTree.tostring(
                image_layer, encoding="utf-8", method="xml"
            ).decode()
            with open(image_prop_file, "a") as myfile:
                myfile.write(xmlstr)
            print("Writing image_props:", image_prop_file)

    def start(self, ds, **kwargs):
        dag_run_id = kwargs["dag_run"].run_id
        batch_folders = sorted(
            [
                f
                for f in glob.glob(
                    os.path.join(
                        self.airflow_workflow_dir,
                        dag_run_id,
                        "batch",
                        "*",
                    )
                )
            ]
        )
        mitk_scenes = []
        for batch_element_dir in batch_folders:
            print("batch_element_dir: " + batch_element_dir)
            path_dir = os.path.basename(batch_element_dir)
            print("operator_in_dir: ", self.operator_in_dir)
            fixed_image = sorted(
                glob.glob(
                    os.path.join(batch_element_dir, self.operator_in_dir, "*.nrrd*"),
                    recursive=True,
                )
                + glob.glob(
                    os.path.join(batch_element_dir, self.operator_in_dir, "*.nii*"),
                    recursive=True,
                )
                + glob.glob(
                    os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"),
                    recursive=True,
                )
            )
            print("Flies: ", fixed_image)
            if len(fixed_image) > 0:
                # check if it is a segmentation, if so, download the referencing images
                mitk_scenes.append(
                    {
                        "file_image": os.path.join(
                            self.operator_in_dir, os.path.basename(fixed_image[0])
                        ),
                        "image_name": "fixed_image",
                    }
                )
            moving_image = sorted(
                glob.glob(
                    os.path.join(batch_element_dir, self.additional_input, "*.nrrd*"),
                    recursive=True,
                )
                + glob.glob(
                    os.path.join(batch_element_dir, self.additional_input, "*.nii*"),
                    recursive=True,
                )
                + glob.glob(
                    os.path.join(batch_element_dir, self.additional_input, "*.dcm*"),
                    recursive=True,
                )
            )
            print("Flies: ", moving_image)
            if len(moving_image) > 0:
                # check if it is a segmentation, if so, download the referencing images
                mitk_scenes.append(
                    {
                        "file_image": os.path.join(
                            self.additional_input, os.path.basename(moving_image[0])
                        ),
                        "image_name": "moving_image",
                    }
                )
            registration_file = sorted(
                glob.glob(
                    os.path.join(batch_element_dir, self.registration_dir, "*.nrrd*"),
                    recursive=True,
                )
                + glob.glob(
                    os.path.join(batch_element_dir, self.registration_dir, "*.nii*"),
                    recursive=True,
                )
                + glob.glob(
                    os.path.join(batch_element_dir, self.registration_dir, "*.dcm*"),
                    recursive=True,
                )
            )

            for index, reg_file in enumerate(registration_file):
                # check if it is a segmentation, if so, download the referencing images
                if "result.1" in reg_file:
                    mitk_scenes.append(
                        {
                            "file_image": os.path.join(
                                self.registration_dir, os.path.basename(reg_file)
                            ),
                            "image_name": "registration_image",
                        }
                    )
                    print("Registraiton result", reg_file)
                else:
                    print("different result, not used in scene: ", reg_file)
            self.createScene(mitk_scenes, batch_element_dir)

    def __init__(
        self,
        dag,
        additional_input,
        registration_dir,
        name="create_mitk_scene",
        **kwargs
    ):
        self.additional_input = additional_input
        self.registration_dir = registration_dir
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
