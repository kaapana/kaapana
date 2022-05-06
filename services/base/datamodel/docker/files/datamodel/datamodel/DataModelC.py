from .DataImporterC import *
from .Database import *
#
class KaapanaDatamodelC:
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.log.info("Initalized Datamodel")
        self.multi_data_importer = MultiImporterC()
        self.dicom_data_importer = DicomDataImporterC()
        self.raw_data_importer = RawDataImporterC()
        #self.query = Query()
    #
    # def get_patient(self, tags: list):
    #
    #
    # def get_data(self, name: str):
    #
    # def get_patient_age_range(self, ages: tuple):
    #
    #
    # def get_studies_study_description(self, study_description: str):
    #
    #
    # def get_series_modality(self, modality: str):
    #
    #
    # def get_segs_to_patient(self, name: str):
    #
    #
    # def get_reference(self, seg: DataEntityB):
    #
    #
    # def get_number_of_instances(self, name: str):



    def get_db_session(self):
        return session


    def import_data(self, content):
        self.multi_data_importer.import_data(content["files"], content["options"])


    def import_dicom(self, content):
        self.log.info("Importing dicom data")
        print(content["files"])
        self.dicom_data_importer.import_data(content["files"], content["options"])


    def import_raw(self, content):
        self.log.info("Raw import not implemented yet")
        #self.raw_data_importer.import_data(content["files"], content["options"])


    def setup_db(self, app):
        Database.setup_db(app)

    def init_db(self):
        Database.init_db()
