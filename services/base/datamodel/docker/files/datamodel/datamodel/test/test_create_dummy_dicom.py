from pathlib import Path
import random
import string
import pydicom
from random import randint
import os
from dicomgenerator.exporter import export
from dicomgenerator.factory import CTDatasetFactory
from pydicom.uid import generate_uid
"""Generate some CT-like DICOM files """

base_dir = Path('/home/hanno/project/kaapana-internal-datamodel/services/base/datamodel/datamodel/test/images/dummy')


def generate_some_dicom_files(base_dir):
    patient = CTDatasetFactory()
    patient.PatientID ='gen-'+ str(randint(3000, 10000000))
    lastname = str(patient.PatientName.family_name)
    patient_path = lastname.replace(" ", "")
    patient.PatientBirthDate = str(randint(1900, 2021)) +'0' + str(randint(1, 9)) + str(randint(10, 28))
    output_dir_patient= os.path.join(base_dir, patient_path)

    for study in range(10):
        StudyInstanceUID = generate_uid()
        patient.StudyInstanceUID = StudyInstanceUID
        output_dir_study = os.path.join(output_dir_patient, str(StudyInstanceUID))
        patient.StudyDescription = ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))
        modality = ['CT', 'MR', 'PT', 'CR', 'US', 'RTIMAGE', 'BI']
        patient.Modality = modality[randint(0, 6)]

        for series in range(10):
            SeriesInstanceUID = generate_uid()
            patient.SeriesInstanceUID = SeriesInstanceUID
            output_dir_series = os.path.join(output_dir_study, str(SeriesInstanceUID))
            if 1== series:
                reference = patient.SOPInstanceUID
                series_ref = patient.SeriesInstanceUID
            if 2 == series:
                patient.Modality = 'SEG'
                #only for testing...
                #patient.add_new([0x0008, 0x1115], 'SQ', "(Sequence with undefined length #=1)")
                #patient.add_new([0xfffe, 0xe000], 'na', "(Item with undefined length #=2)")
                #patient.add_new([0x0008, 0x1150], 'UI', "CTImageStorage")
                patient.add_new([0x0008, 0x1155], 'UI', reference)
                #patient.add_new([0xfffe, 0xe00d], 'na', "(Item with undefined length #=2)")
                #patient.add_new([0x0020, 0x000e], 'UI', series_ref)
            filenames = [f"dcmincance{x}.dcm" for x in range(5)]
            for filename in filenames:
                #same series and study
                patient.SOPInstanceUID = generate_uid()
                print(patient.Modality)
                path = Path(output_dir_series)
                path.mkdir(parents=True, exist_ok=True)
                export(dataset=patient, path=path/ filename)

            print(f"Wrote {len(filenames)} files to {output_dir_series}")


generate_some_dicom_files(base_dir)