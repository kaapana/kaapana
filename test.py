import os
from dicomweb_client.api import DICOMwebClient
import pydicom
import requests


class DICOMUploader:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        session = requests.Session()
        session.verify = False
        self.client = DICOMwebClient(
            url="https://193.174.50.103/dicomweb:7777", session=session
        )

    def upload_files(self):
        print(f"Uploading files from {self.folder_path}...")
        dicom_files = [
            f for f in os.listdir(self.folder_path) if f.lower().endswith(".dcm")
        ]
        for dicom_file in dicom_files:
            file_path = os.path.join(self.folder_path, dicom_file)
            with open(file_path, "rb") as f:
                ds = pydicom.dcmread(f)
                try:
                    self.client.store_instances([ds])
                    print(f"Successfully uploaded {dicom_file} with SOPInstanceUID {ds.SOPInstanceUID}")
                except Exception as e:
                    print(f"Failed to upload {dicom_file}: {str(e)}")


if __name__ == "__main__":
    uploader = DICOMUploader(
        "/media/b556m/slow_data_dir/b556m/Downloads/TCIA/manifest-1680277513580/CT Lymph Nodes/ABD_LYMPH_002/09-14-2014-ABDLYMPH002-abdominallymphnodes-40168/300.000000-Lymph node segmentations-32864",
    )
    uploader.upload_files()
