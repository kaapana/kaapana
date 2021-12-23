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

class DataImporter:
    def __init__(self):
        self.log = logging.getLogger(__name__)

#     def setPermission(self, aetitle_ownership):
#         group = AccessData.GetKeycloakGroupModels(aetitle_ownership)
# #        permission = self.accessData.GetPermission(type=DataImporter)
#         return DatabaseImporter.add_access(group)#, permission=permission)


class MultiImporter(DataImporter):
    def __init__(self):
        self.importers = [
            DicomDataImporter(),
            RawDataImporter()
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


class DicomDataImporter(DataImporter):
    def __init__(self):
        #self.dcm2json = Dcm2Json(delete_private_tags=False)
        self.dcm2jsonConverter = Dcm2JsonConverter(delete_private_tags=False)
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
        for file in files:
            # Step 1 - Make file Acessible
            ds = dcmread(file)

            # Step 2 - Indexing

            patient_name = ds[0x0010, 0x0010].value
            family_name = str(patient_name.family_name)
            given_name = str(patient_name.given_name)
            patient_id = str(ds[0x0010, 0x0020].value)
            birthday = str(ds[0x0010, 0x0030].value)

            if len(birthday) == 8:
                try:
                    birth_day = datetime(year=int(birthday[0:4]),
                                                  month=int(birthday[4:6]),
                                                  day=int(birthday[6:8]))
                except:
                    logging.debug("Birthday not correct format: ", birthday)
                    birth_day = None

            else:
                logging.debug("Birthday is empty or has a wrong fromat, using a default value")
                birth_day = None
            if patient_name_last != patient_name and patient_id_last != patient_id:
                patient = DatabaseImporter.add_patient(family_name=family_name,
                                                       given_name=given_name,
                                                       birthday=birth_day,
                                                       patient_id=patient_id)
                patient_name_last = patient_name
                patient_id_last = patient_id

            study_uid = str(ds[0x0020, 0x000D].value)
            if study_uid_last != study_uid:
                # TODO: store_aet, can mabe diverse
                store_aet = 'kaapana'
                # Permission
                #access = self.setPermission(store_aet)
                study = DatabaseImporter.add_study(study_uid=study_uid,
                                                   patient=patient, access=store_aet)
                study_uid_last = study_uid

            series_uid = str(ds[0x0020, 0x000E].value)
            if series_uid_last != series_uid:
                #json_dict = self.dcm2json.start(file)
                json_dict = self.dcm2jsonConverter.start(file)
                series = DatabaseImporter.add_series(series_uid=series_uid,
                                            study=study,
                                            json_dict=json_dict)
                series_uid_last = series_uid
            instance_uid = str(ds[0x0008, 0x0018].value)
            file = File.add(path=instance_uid, location="PACs")
            #TODO add in new class series
            series.dicom_instances.append(file)

        Database.commit_to_db()





class RawDataImporter(DataImporter):

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