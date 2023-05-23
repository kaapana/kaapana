from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from xml.etree import ElementTree
import os
import json
from dicomweb_client.api import DICOMwebClient
import pydicom
import time
import glob
import requests


class LocalMiktInputOperator(KaapanaPythonBaseOperator):
    def downloadSeries(self, studyUID: str, seriesUID: str, target_dir: str):
        print("Downloading Series: %s" % seriesUID)
        print("Target DIR: %s" % target_dir)

        dcm_web = HelperDcmWeb()
        result = dcm_web.downloadSeries(seriesUID=seriesUID, target_dir=target_dir)
        return result

    def createTasklist(self, run_dir: str, tasks: list()):
        print(
            "create json tasklist and dump it to batch level of the current airflow task run,"
        )
        tasklist = dict()
        tasklist["FileFormat"] = "MITK Segmentation Task List"
        tasklist["Version"] = 1
        tasklist["Name"] = "Kaapana Task List"
        tasklist["Tasks"] = tasks

        with open(
            os.path.join(run_dir, self.batch_name, "tasklist.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(tasklist, f, ensure_ascii=False, indent=4)

    def get_files(self, ds, **kwargs):
        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = [
            f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))
        ]

        print("Starting module MtikInputOperator")

        tasks = list()
        number = 0
        for batch_element_dir in batch_folder:
            print("batch_element_dir: " + batch_element_dir)
            path_dir = os.path.basename(batch_element_dir)
            print("operator_in_dir: ", self.operator_in_dir)
            dcm_files = sorted(
                glob.glob(
                    os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"),
                    recursive=True,
                )
            )
            print("Dicom files: ", dcm_files)
            if len(dcm_files) > 0:
                task = dict()
                incoming_dcm = pydicom.dcmread(dcm_files[0])
                seriesUID = incoming_dcm.SeriesInstanceUID
                patientID = incoming_dcm.PatientID + " task " + str(number)
                number = number + 1
                # check if it is a segmentation, if so, download the referencing images
                if "ReferencedSeriesSequence" in incoming_dcm:
                    reference = incoming_dcm.ReferencedSeriesSequence
                    seriesUID = reference._list[0].SeriesInstanceUID
                    REF_IMG = "REF_IMG"
                    target_dir = os.path.join(batch_element_dir, REF_IMG)
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir)

                    result = self.downloadSeries(
                        studyUID=incoming_dcm.StudyInstanceUID,
                        seriesUID=seriesUID,
                        target_dir=target_dir,
                    )
                    if result:
                        dcm_image = sorted(
                            glob.glob(
                                os.path.join(target_dir, "*.dcm*"), recursive=True
                            )
                        )
                        task["Image"] = os.path.join(
                            path_dir, REF_IMG, os.path.basename(dcm_image[0])
                        )
                        task["Segmentation"] = os.path.join(
                            path_dir,
                            self.operator_in_dir,
                            os.path.basename(dcm_files[0]),
                        )
                    else:
                        print("Reference images to segmentation not found!")
                        raise ValueError("ERROR")
                # otherwise only open images without segmentation
                else:
                    print("No segementaion, create scene with image only")
                    task["Image"] = os.path.join(
                        path_dir, self.operator_in_dir, os.path.basename(dcm_files[0])
                    )
                task["Result"] = os.path.join(
                    path_dir, self.operator_out_dir, "result.dcm"
                )
                task["Name"] = patientID
                tasks.append(task)
                print("task successfully added:")
                print(task)
        self.createTasklist(run_dir, tasks)

    def __init__(
        self,
        dag,
        pacs_dcmweb_host="http://dcm4chee-service.store.svc",
        pacs_dcmweb_port="8080",
        operator_out_dir="mitk-results",
        aetitle="KAAPANA",
        **kwargs
    ):
        self.pacs_dcmweb = (
            pacs_dcmweb_host
            + ":"
            + pacs_dcmweb_port
            + "/dcm4chee-arc/aets/"
            + aetitle.upper()
        )

        super().__init__(
            dag=dag,
            name="get-mitk-input",
            operator_out_dir=operator_out_dir,
            python_callable=self.get_files,
            **kwargs
        )
