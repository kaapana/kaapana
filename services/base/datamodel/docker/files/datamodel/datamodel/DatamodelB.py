import json
import logging

import sqlalchemy.orm
from .DataImporterB import *
from .Database import *
from datetime import datetime
# from InitalDataModel import DataImporter, DicomDataImporter
from sqlalchemy import Integer
#
class KaapanaDatamodelB:
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.log.info("Initalized Datamodel")
        self.multi_data_importer = MultiImporterB()
        self.dicom_data_importer = DicomDataImporterB()
        self.raw_data_importer = RawDataImporterB()
        #self.query = Query()



    def get_patient(self, tags: list):
        #Todo more general query option
        # add_to_filter = []
        # for tag in tags:
        #   colum = column_tag_check(tag)
        #   add_to_filter.....
        "not implemented yet"

    def get_data(self, name: str):
        dicompatient = session().query(DataEntityB).filter(DataEntityB.meta['00100010']['QueryValue'].astext.like('%{0}%'.format(name))).all()

        return dicompatient

    def get_patient_age_range(self, ages: tuple):
        age_max = int(ages[1][6:] + ages[1][3:5] + ages[1][:2])
        age_min = int(ages[0][6:] + ages[0][3:5] + ages[0][:2])
        entity = session().query(DataEntityB).filter(DataEntityB.meta['00100030']['QueryValue'].astext.cast(Integer) <= age_max).\
            filter(DataEntityB.meta['00100030']['QueryValue'].astext.cast(Integer) >= age_min).all()
        return entity

    def get_studies_study_description(self, study_description: str):
        dicom_study = session().query(DataEntityB).filter(DataEntityB.meta['00081030']['QueryValue'].astext == study_description).all()
        return dicom_study

    def get_series_modality(self, modality: str):
        series = session().query(DataEntityB)\
            .filter(DataEntityB.meta['00080060']['QueryValue'] == json.dumps(modality)).all()
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
        #TODO how to select data from connected Entities????????????????????????????????????????
        #Two Stages:
        patient_entity = session().query(DataEntityB) \
            .filter(DataEntityB.meta['00100010']['QueryValue'].astext.like('%{0}%'.format(name))).first()
        patient = session().query(DataEntityB) \
            .filter(DataEntityB == patient_entity)\
            .filter(DataEntityB.meta['00080060']['QueryValue'].astext == 'SEG').all()
        if patient:
            return patient
        studies = session().query(DataEntityB)\
            .join(Link.source)\
            .filter(Link.target == patient_entity)\
            .filter(DataEntityB.meta['00080060']['QueryValue'].astext == 'SEG').all()


        if studies:
            return studies

        studies = session().query(DataEntityB)\
            .join(Link.source)\
            .filter(Link.target == patient_entity).all()

        cond = sqlalchemy.sql.or_(False, *[Link.target == p for p in studies])
        # series = session().query(DataEntityB) \
        #     .join(Link.source) \
        #     .filter(cond).all()

        series = session().query(DataEntityB) \
            .join(Link.source) \
            .filter(cond)\
            .filter(DataEntityB.meta['00080060']['QueryValue'].astext == 'SEG').all()

        return series
        #  seg_series = session().query(DataEntityB)\
        #      .filter(DataEntityB.meta['00100010']['QueryValue'].astext.like('%{0}%'.format(name)))\
        #     .filter(DataEntityB.meta['00080060']['QueryValue'].astext == 'SEG').all()
        #
        # return seg_series

    def get_reference(self, seg: DataEntityB):
        #ref_uid = seg.meta['0020000E']['QueryValue']
        #ref_series = session().query(DataEntityB).filter(DataEntityB.meta['00081155']['QueryValue'].astext == ref_uid).all()
        return 0#ref_series

    def get_number_of_instances(self, name: str):
        patient_entity = session().query(DataEntityB)\
            .filter(DataEntityB.meta['00100010']['QueryValue'].astext.like('%{0}%'.format(name))).first()
        studies = session().query(DataEntityB)\
            .join(Link.source)\
            .filter(Link.target == patient_entity).all()
        studies_target = [Link.target == p for p in studies]
        cond = sqlalchemy.sql.or_(False, *studies_target)
        series = session().query(DataEntityB) \
            .join(Link.source) \
            .filter(cond).all()
        series_target = [Link.target == p for p in series]
        cond = sqlalchemy.sql.or_(False, *series_target)

        number_of_instances = session().query(DataEntityB) \
            .join(Link.source) \
            .filter(cond).count()

        # patient = session().query(DataEntityB)\
        #     .filter(DataEntityB.meta['00100010']['QueryValue'].astext.like('%{0}%'.format(name))).subquery()
        # studies = session().query(patient).join(Link.source)\
        #     .filter(Link.target_id == patient.c.id).subquery()
        # series = session().query(studies).join(Link.source)\
        #     .filter(Link.target_id == studies.c.id).subquery()
        # number_of_instances = session().query(series).join(Link.source)\
        #     .filter(Link.target_id == series.c.id).count()
        return number_of_instances



    def get_db_session(self):
        return session


    def import_data(self, content):
        self.multi_data_importer.import_data(content["files"], content["options"])


    def import_dicom(self, content):
        self.log.info("Importing dicom data")
        logging.info(content["files"])
        self.dicom_data_importer.import_data(content["files"])


    def import_raw(self, content):
        self.log.info("Raw import not implemented yet")
        #self.raw_data_importer.import_data(content["files"], content["options"])


    def setup_db(self, app):
        Database.setup_db(app)

    def init_db(self):
        Database.init_db()
