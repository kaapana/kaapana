import datetime
import logging
import os.path
from .Database import *
from pydicom import dcmread
from pydicom.errors import InvalidDicomError
from .Dcm2Json import Dcm2Json
from .Dcm2JsonConverter import Dcm2JsonConverter
from .Dataset import Dataset
from .File import File

class DataImporterB:
    def __init__(self):
        self.log = logging.getLogger(__name__)

#     def setPermission(self, aetitle_ownership):
#         group = AccessData.GetKeycloakGroupModels(aetitle_ownership)
# #        permission = self.accessData.GetPermission(type=DataImporter)
#         return DatabaseImporter.add_access(group)#, permission=permission)


class MultiImporterB(DataImporterB):
    def __init__(self):
        self.importers = [
            DicomDataImporterB(),
            RawDataImporterB()
        ]

    def can_import(self, path):
        for i in self.importers:
            if i.can_import(path):
                return True
        return False

    def import_data(self, files, options = None):
        # expects homogenous files (e.g. all dicom)
        for i in self.importers:
            if i.can_import(files[0]):
                i.import_data(files, options)
                return
        raise Exception("No importer found")


class DicomDataImporterB(DataImporterB):
    def __init__(self):
        self.dcm2jsonConverter = Dcm2JsonConverter(delete_private_tags=False)
        #self.dcm2json = Dcm2Json(delete_private_tags=False)

        super().__init__()


    def can_import(self, path):
        try:
            ds = dcmread(path)
        except InvalidDicomError:
            return False
        return True

    def import_data(self, files, options=None):
        patient_name_last = None
        patient_id_last = None
        study_uid_last = None
        series_uid_last = None
        # Step 0 before the datamodel (or TODO maybe after, and add path later
        storage_path = None
        if "storage_path" in options:
            storage_path = options["storage_path"]
        entityB_collection_series = []
        entityB_collection_study = []
        entityB_collection_patient = []
        for file in files:
            #json_dict = self.dcm2json.start(file)
            json_dict = self.dcm2jsonConverter.start(file)
            entityB = DatabaseImporter.add_entityB(meta=json_dict)
            entityB_collection_series.append(entityB)
            ds = dcmread(file)
            patient_name = ds[0x0010, 0x0010].value
            patient_id = str(ds[0x0010, 0x0020].value)
            study_uid = str(ds[0x0020, 0x000D].value)
            series_uid = str(ds[0x0020, 0x000E].value)
            if series_uid_last and series_uid_last != series_uid:
                series = DatabaseImporter.add_collection(dataentities=entityB_collection_series, type="DicomInstance2SeriesLink")
                entityB_collection_series = []
                entityB_collection_study.append(series)
                series_uid_last = series_uid
            if study_uid_last and study_uid_last != study_uid:
                # TODO: store_aet, can mabe diverse
                study = DatabaseImporter.add_collection(dataentities=entityB_collection_study, type="DicomSeries2StudyLink")
                entityB_collection_patient.append(study)
                entityB_collection_study = []
                study_uid_last = study_uid
            if patient_name_last and patient_name_last != patient_name and patient_id_last != patient_id:
                patient = DatabaseImporter.add_collection(dataentities=entityB_collection_patient, type="DicomStudy2PatientLink")
                patient_name_last = patient_name
                patient_id_last = patient_id

                series_uid_last = series_uid

        series = DatabaseImporter.add_collection(dataentities=entityB_collection_series, type="DicomInstance2SeriesLink")
        entityB_collection_study.append(series)
        study = DatabaseImporter.add_collection(dataentities=entityB_collection_study, type="DicomSeries2StudyLink")
        entityB_collection_patient.append(study)
        patient = DatabaseImporter.add_collection(dataentities=entityB_collection_patient, type="DicomStudy2PatientLink")


        Database.commit_to_db()





class RawDataImporterB(DataImporterB):

    def can_import(self, path):
        return True

    def import_data(self, files, options=None):
        # Step 0 before the datamodel (or TODO maybe after, and add path later
        if options and "folder" in options:
            folder = options["folder"]

        ownership = "todo" #options["aetitle_ownership"]
        #access = self.setPermission(ownership)
        path = storage_path = ""
        file_data_entities = []
        for file in files:
            path, filename = os.path.split(file)
            file = File.add(path=file, location="S3")
            if storage_path == path or storage_path == "":
                file_data_entities.append(file.data_entity)
            else:
                Dataset.add_generated(name=path, set_entities=file_data_entities, access=ownership)
                file_data_entities = []
            storage_path = path
        Dataset.add_generated(name=path, set_entities=file_data_entities, access=ownership)
        Database.commit_to_db()