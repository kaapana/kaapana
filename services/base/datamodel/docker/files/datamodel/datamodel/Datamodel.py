import json
import logging
from .DataImporter import *
from .Database import *
# from InitalDataModel import DataImporter, DicomDataImporter
#
class KaapanaDatamodel:
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.log.info("Initalized Datamodel")
        self.multi_data_importer = MultiImporter()
        self.dicom_data_importer = DicomDataImporter()
        self.raw_data_importer = RawDataImporter()
        #self.query = Query()



    def get_patient(self, tags: list):
        #Todo more general query option
        # add_to_filter = []
        # for tag in tags:
        #   colum = column_tag_check(tag)
        #   add_to_filter.....
        "not implemented yet"

    def get_data(self, name: str):
        dicompatient = session().query(DicomPatient).filter(DicomPatient.family_name == name).all()
        # all_series =[]
        # for patient in dicompatient:
        #     studies = patient.dicom_studies
        #     for study in studies:
        #         all_series.append(study.dicom_series)
        return dicompatient

    def get_patient_age_range(self, ages: tuple):
        age_max= datetime(year=int(ages[1][6:]),
                   month=int(ages[1][3:5]),
                   day=int(ages[1][:2]))
        age_min =datetime(year=int(ages[0][6:]),
                   month=int(ages[0][3:5]),
                   day=int(ages[0][:2]))
        dicompatient = session().query(DicomPatient).filter(DicomPatient.birthday <= age_max).\
            filter(DicomPatient.birthday >= age_min).all()
        return dicompatient

    def get_studies_study_description(self, study_description: str):
        dicom_study = session().query(DicomStudy).filter(DicomStudy.study_description == study_description).all()
        return dicom_study

    def get_series_modality(self, modality: str):
        series = session().query(DicomSeries.meta)\
            .filter(DicomSeries.meta['00080060']['QueryValue'] == json.dumps(modality)).all()
        # series = session().query(DicomSeries)\
        #     .with_hint(DicomSeries, 'USE INDEX (dicom_series_modality)')\
        #     .filter(DicomSeries.meta['00080060 Modality_keyword'].astext == modality).all()

        # print(session().query(DicomSeries)\
        #     .filter(DicomSeries.meta['00080060 Modality_keyword'].astext == modality))
        # series = session().query(DicomSeries)\
        #     .filter("SELECT meta FROM dicom_series WHERE meta @> {'00080060 Modality_keyword': modality}").all()
        # modality_key = "00080060 Modality_keyword"
        # qu_str = str({modality_key: modality})
        # sql_query = "SELECT * FROM dicom_series WHERE meta @> '{}';".format(qu_str)
        # series = session().execute(sql_query)
        return series

    def get_segs_to_patient(self, name: str):
        seg_series = session().query(DicomSeries).\
                      join(DicomStudy).\
                      join(DicomPatient).\
                      filter(DicomPatient.family_name == name).\
                      filter(DicomSeries.meta['00080060']['QueryValue'].astext == 'SEG').all()

        return seg_series

    def get_reference(self, seg: DicomSeries):
        #ref_uid= seg.meta['0020000E SeriesInstanceUID_keyword']
        #ref_series = session().query(DicomSeries).filter(DicomSeries.series_uid == ref_uid).all()
        return 0

    def get_number_of_instances(self, name: str):
        number_of_instances = session().query(File)\
            .join(DicomSeries).join(DicomStudy).join(DicomPatient)\
            .filter(DicomPatient.family_name == name).count()
        return number_of_instances



    def get_db_session(self):
        return session


    def import_data(self, content):
        self.multi_data_importer.import_data(content["files"], content["options"])


    def import_dicom(self, content):
        self.log.info("Importing dicom data")
        print(content["files"])
        self.dicom_data_importer.import_data(content["files"], content["options"])


    def import_raw(self, content):
        self.log.info("Importing dicom data")
        self.raw_data_importer.import_data(content["files"], content["options"])


    def setup_db(self, app):
        Database.setup_db(app)

    def init_db(self):
        Database.init_db()
