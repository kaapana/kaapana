import logging
from .Database import *
from pydicom import dcmread
from pydicom.errors import InvalidDicomError

from .database.pydantic_model import SchemaModelConverter
from datamodel.dicommetadata.extractor import Extractor

class DataImporterC:
    def __init__(self):
        self.log = logging.getLogger(__name__)

#     def setPermission(self, aetitle_ownership):
#         group = AccessData.GetKeycloakGroupModels(aetitle_ownership)
# #        permission = self.accessData.GetPermission(type=DataImporter)
#         return DatabaseImporter.add_access(group)#, permission=permission)


class MultiImporterC(DataImporterC):
    def __init__(self):
        self.importers = [
            DicomDataImporterC(),
            RawDataImporterC()
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


class DicomDataImporterC(DataImporterC):
    def __init__(self):
        #add different converter TODO
        #self.dcm2jsonConverter = Dcm2JsonConverter(delete_private_tags=False)
        self.dicomextractor = Extractor()
        #self.dcm2json = Dcm2Json(delete_private_tags=False)

        super().__init__()


    def can_import(self, path):
        try:
            ds = dcmread(path)
        except InvalidDicomError:
            return False
        return True




    def dicom_extractor(self, modules: dict):
        meta_list = list()
        for module in modules:
            if "type" in module:
                type = module["type"]
                meta = SchemaModelConverter.mapper(module, type)
            else:
                meta = module
                meta['type'] = 'unknown'
            meta_list.append(meta)
        entities_with_type = list()
        linker_list = list()
        for meta in meta_list:
            linker = meta.pop('links')
            entity = DatabaseImporter.add_entityB(meta)
            for link in linker:
                if 'source' in link:
                    link['target_entity'] = entity
                if 'target' in link:
                    link['source_entity'] = entity
                linker_list.append(link)
            #this is needed, sind not all entities might have a defined link
            entities_with_type.append({'entity': entity,
                               'type': meta['type']})
        for links in linker_list:
                if 'source' in links:
                    for part in entities_with_type:
                        if part['type'] == links['source']:
                            DatabaseImporter.add_linker(source=part['entity'],
                                                                 target=links['target_entity'],
                                                                 type=links['source'] + "2" + links['target_type'])
                            break
                if 'target' in links:
                    for part in entities_with_type:
                        if part['type'] == links['target']:
                            DatabaseImporter.add_linker(source=links['source_entity'],
                                                        target=part['entity'],
                                                        type=links['source_type'] + "2" + links['target'])
                            break

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
            #json_dict = self.dcm2jsonConverter.start(file)
            modules = self.dicomextractor.get_modules(file)
            self.dicom_extractor(modules)
            Database.commit_to_db()





class RawDataImporterC(DataImporterC):

    def can_import(self, path):
        return True

    def import_data(self, files, options=None):
        # Step 0 before the datamodel (or TODO maybe after, and add path later
        # if options and "folder" in options:
        #     folder = options["folder"]
        #
        # ownership = "todo" #options["aetitle_ownership"]
        # #access = self.setPermission(ownership)
        # path = storage_path = ""
        # file_data_entities = []
        # for file in files:
        #     path, filename = os.path.split(file)
        #     file = File.add(path=file, location="S3")
        #     if storage_path == path or storage_path == "":
        #         file_data_entities.append(file.data_entity)
        #     else:
        #         Dataset.add_generated(name=path, set_entities=file_data_entities, access=ownership)
        #         file_data_entities = []
        #     storage_path = path
        # Dataset.add_generated(name=path, set_entities=file_data_entities, access=ownership)
        Database.commit_to_db()