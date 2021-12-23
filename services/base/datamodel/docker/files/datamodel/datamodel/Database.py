import logging

from flask_graphql import GraphQLView
from datetime import datetime
from datamodel.database.model_dicom import DicomPatient, DicomStudy, DicomSeries
from datamodel.database.model_raw import File
from datamodel.database.model_permission import Access
from datamodel.database.model import DataEntity
from datamodel.database.base import commit_to_db, add_to_session, init_db, refresh, session, add_and_commit_to_session
from sqlalchemy.orm.query import Query
import typing
from datamodel.database.modelB import DataEntityB, Collection, Link
from sqlalchemy.orm.attributes import flag_modified
from deepdiff import DeepDiff, Delta
import re
class DatabaseImporter:


    @staticmethod
    def add_access(data_entity: DataEntity, keycloak_group: str) -> bool:
        if keycloak_group:
            access: Access = Access.query.filter(Access.group == keycloak_group).first()
            if access:
                if keycloak_group not in data_entity.accesses:
                    data_entity.accesses.append(access)
                    return True
                return False
            access = Access(group=keycloak_group)
            data_entity.accesses.append(access)
            add_to_session(access)
            return True

    @staticmethod
    def add_data_entity(keycloak_group=None) -> DataEntity:
        data_entity = DataEntity()
        if keycloak_group:
            DatabaseImporter.add_access(data_entity=data_entity, keycloak_group=keycloak_group)
        add_to_session(data_entity)
        return data_entity

    @staticmethod
    def add_patient(family_name: str, given_name: str, birthday: datetime, patient_id: str) -> DicomPatient:
        exists: DicomPatient = DicomPatient.query.filter(DicomPatient.patient_uid == patient_id).first()
        if exists:
            return exists
        if not birthday:
            birthday = None
        data_entity = DatabaseImporter.add_data_entity()
        patient_new = DicomPatient(family_name=family_name,
                                   given_name=given_name,
                                   birthday=birthday,
                                   patient_uid=patient_id,
                                   data_entity=data_entity
                                   )
        #patient = Patient(name=patient_name, patient_id=patient_id)
        add_to_session(patient_new)
        #Database.commit_to_db()
        return patient_new

    @staticmethod
    def add_study(study_uid: str, patient: DicomPatient, access: str) -> DicomStudy:
        exists: DicomStudy = DicomStudy.query.filter(DicomStudy.study_uid == study_uid).first()
        if exists:
            is_added = DatabaseImporter.add_access(data_entity=exists.data_entity,
                                                 keycloak_group=access)

            #TODO: how to handle json_meta?? compare? sort? overwrite?...

            if is_added:
                add_to_session(exists)
            return exists
        data_entity = DatabaseImporter.add_data_entity(keycloak_group=access)
        study = DicomStudy(study_uid=study_uid, dicom_patient=patient, data_entity=data_entity)

        #data_flags_dummy = {"key1": [1, 2, 3], "key2": "xx"}
        #study.meta = data_flags_dummy

        add_to_session(study)
        return study

    @staticmethod
    def add_series(series_uid: str, study: DicomStudy, json_dict: dict) -> DicomSeries:
        exists: DicomSeries = DicomSeries.query.filter(DicomSeries.series_uid == series_uid).first()
        if exists:
            return exists
        data_entity = DatabaseImporter.add_data_entity()
        if not study.study_description:
            study.study_description = json_dict['00081030']['QueryValue']
            add_to_session(study)
        series = DicomSeries(series_uid=series_uid,
                             dicom_study=study,
                             meta=json_dict,
                             data_entity=data_entity)
        add_to_session(series)
        return series

    @staticmethod
    def remove_access(data_entity: DataEntity, keycloak_group: str) -> bool:
        access: Access = Access.query.filter(Access.group == keycloak_group).first()
        if access:
            data_entity.accesses.remove(access)
            return True
        return False

    @staticmethod
    #Todo move somewher else
    def find_diff_dict(dict1 :dict, dict2: dict) -> tuple:
        meta_dict = {}
        meta_base_dict = {}
        for (tag, data) in dict1.items():
            try:
                data2 = dict2[tag]
                if data == data2:
                    continue
                meta_dict[tag] = dict2[tag]
                meta_base_dict[tag] = dict1[tag]
            except KeyError as e:
                print(f"KeyError {e}")
                continue

        # ddiff = DeepDiff(dict1, dict2, ignore_order=True, report_repetition=True)
        # meta_dict = {}
        # meta_base_dict = {}
        # if 'values_changed' in ddiff:
        #     all_changed_diff = ddiff['values_changed']
        #     for values_changed in all_changed_diff:
        #         key = re.search("'(.+?)'", values_changed).group(1)
                # meta_dict[key] = dict2[key]
                # meta_base_dict[key] = dict1.pop(key)

        # do not add new items, because otherwise meta for example in series is compared to meta with everything (witch is in patient)
        # if 'dictionary_item_added' in ddiff:
        #     all_added_val = ddiff['dictionary_item_added']
        #     for values_changed in all_added_val:
        #         key = re.search("'(.+?)'", values_changed).group(1)
        #         meta_dict[key] = dict2[key]

        return meta_dict, meta_base_dict, dict1

    @staticmethod
    def add_entityB(meta: dict) -> DataEntityB:
        instance: DataEntityB = DataEntityB.query\
            .filter(DataEntityB.meta['00080018']['QueryValue'].astext == meta['00080018']['QueryValue']).first()
        if instance:
            return instance
        ##save only always diff in second instance.--.
        series = DataEntityB.query. \
            filter(DataEntityB.meta['0020000E']['QueryValue'].astext == meta[
            '0020000E']['QueryValue']).first()
        if series:
            # https://github.com/seperman/deepdiff
            # create instance
            instances = DataEntityB.query.join(Link.source).filter(Link.target == series).all()
            study = DataEntityB.query.join(Link.target).filter(Link.source == series).first()
            patient = DataEntityB.query.join(Link.target).filter(Link.source == study).first()
            #remove all other tags
            for tag in list(patient.meta.keys()):
                try:
                    if patient.meta[tag] == meta[tag]:
                        meta.pop(tag)
                    elif len(instances) > 0:
                        tag_value = patient.meta.pop(tag)
                        for instance in instances:
                            instance.meta[tag] = tag_value
                            flag_modified(instance, "meta")
                        flag_modified(patient, "meta")
                except Exception as e:#KeyError as e:
                    print(f"KeyError {e}")
                    continue
            for tag in list(study.meta.keys()):
                try:
                    if study.meta[tag] == meta[tag]:
                        meta.pop(tag)
                    elif len(instances) > 0:
                        tag_value = study.meta.pop(tag)
                        for instance in instances:
                            instance.meta[tag] = tag_value
                            flag_modified(instance, "meta")
                        flag_modified(study, "meta")
                except KeyError as e:
                    print(f"KeyError {e}")
                    continue
            for tag in list(series.meta.keys()):
                try:
                    if series.meta[tag] == meta[tag]:
                        meta.pop(tag)
                    elif len(instances) > 0:
                        tag_value = series.meta.pop(tag)
                        for instance in instances:
                            instance.meta[tag] = tag_value
                            flag_modified(instance, "meta")
                        flag_modified(series, "meta")
                except KeyError as e:
                    print(f"KeyError {e}")
                    continue
            commit_to_db()
            instance1 = DataEntityB(meta=meta)
            add_and_commit_to_session(instance1)
            DatabaseImporter.add_linker(instance1, series, "DicomInstance2Series")
            return instance1 # todo instance0??
        study = DataEntityB.query. \
            filter(DataEntityB.meta['0020000D']['QueryValue'].astext == meta['0020000D']['QueryValue']).first()
        if study:
            series = DataEntityB.query.join(Link.source).filter(Link.target == study).all()
            patient = DataEntityB.query.join(Link.target).filter(Link.source == study).first()
            #remove all other tags
            for tag in list(patient.meta.keys()):
                try:
                    if patient.meta[tag] == meta[tag]:
                        meta.pop(tag)
                    elif len(series) > 0:
                        tag_value = patient.meta.pop(tag)
                        for series_single in series:
                            series_single.meta[tag] = tag_value
                            flag_modified(series_single, "meta")
                        flag_modified(patient, "meta")
                except KeyError as e:
                    print(f"KeyError {e}")
                    continue
            for tag in list(study.meta.keys()):
                try:
                    if study.meta[tag] == meta[tag]:
                        meta.pop(tag)
                    elif len(series) > 0:
                        tag_value = study.meta.pop(tag)
                        for series_single in series:
                            series_single.meta[tag] = tag_value
                            flag_modified(series_single, "meta")
                        flag_modified(patient, "meta")
                except KeyError as e:
                    print(f"KeyError {e}")
                    continue
            commit_to_db()
            # move tags of series 0 to series level
            serie_new_meta = {}
            for tag in list(series[0].meta.keys()):
                try:
                    if tag in meta:
                        serie_new_meta[tag] = meta.pop(tag)
                except KeyError as e:
                    print(f"KeyError {e}")
                    continue
            new_series = DataEntityB(meta=serie_new_meta)
            add_and_commit_to_session(new_series)
            DatabaseImporter.add_linker(new_series, study, "DicomSeries2Study")
            instance1 = DataEntityB(meta=meta)
            add_and_commit_to_session(instance1)
            DatabaseImporter.add_linker(instance1, new_series, "DicomInstance2Series")
            return instance1 # todo add instance0

        patient = DataEntityB.query. \
            filter(DataEntityB.meta['00100020']['QueryValue'].astext == meta[
            '00100020']['QueryValue']).first()
        if patient:
            studies = DataEntityB.query.join(Link.source).filter(Link.target == patient).all()
            series = DataEntityB.query.join(Link.source).filter(Link.target == studies[0]).first()

            for tag in list(patient.meta.keys()):
                try:
                    if patient.meta[tag] == meta[tag]:
                        meta.pop(tag)
                    elif len(studies) > 0:
                        tag_value = patient.meta.pop(tag)
                        for study in studies:
                            study.meta[tag] = tag_value
                            flag_modified(study, "meta")
                        flag_modified(patient, "meta")
                except KeyError as e:
                    print(f"KeyError {e}")
                    continue
            study_new_meta = {}
            for tag in list(studies[0].meta.keys()):
                try:
                    if tag in meta:
                        study_new_meta[tag] = meta.pop(tag)
                except KeyError as e:
                    print(f"KeyError {e}")
                    continue
            # meta with study,series,and instance
            serie_new_meta = {}
            for tag in list(series.meta.keys()):
                try:
                    if tag in meta:
                        serie_new_meta[tag] = meta.pop(tag)
                except KeyError as e:
                    print(f"KeyError {e}")
                    continue
            commit_to_db()
            new_study = DataEntityB(meta=study_new_meta)
            add_and_commit_to_session(new_study)
            DatabaseImporter.add_linker(new_study, patient, "DicomStudyPatient")
            new_series = DataEntityB(meta=serie_new_meta)
            add_and_commit_to_session(new_series)
            DatabaseImporter.add_linker(new_series, new_study, "DicomSeries2Study")
            instance1 = DataEntityB(meta=meta)
            add_and_commit_to_session(instance1)
            DatabaseImporter.add_linker(instance1, new_series, "DicomInstance2Series")
            return instance1 # todo add instance0
        first_study = {}
        first_series = {}
        first_instance = {}
        first_study['0020000D'] = meta.pop('0020000D')
        first_series['0020000E'] = meta.pop('0020000E')
        first_instance['00080018'] = meta.pop('00080018')

        entity_patient = DataEntityB(meta=meta)
        entity_study= DataEntityB(meta=first_study)
        entity_series = DataEntityB(meta=first_series)
        entity_instance = DataEntityB(meta=first_instance)
        add_and_commit_to_session(entity_patient)
        add_and_commit_to_session(entity_study)
        add_and_commit_to_session(entity_series)
        add_and_commit_to_session(entity_instance)
        DatabaseImporter.add_linker(entity_study, entity_patient, "DicomStudy2Patient")
        DatabaseImporter.add_linker(entity_series, entity_study, "DicomSeries2Study")
        DatabaseImporter.add_linker(entity_instance, entity_series, "DicomInstance2Series")
        return entity_instance

    # @staticmethod
    # def add_entityB(meta: dict) -> DataEntityB:
    #     instance: DataEntityB = DataEntityB.query\
    #         .filter(DataEntityB.meta['00080018']['QueryValue'].astext == meta['00080018']['QueryValue']).first()
    #     if instance:
    #         return instance
    #     ##save only always diff in second instance.--.
    #     series = DataEntityB.query. \
    #         filter(DataEntityB.meta['0020000E']['QueryValue'].astext == meta[
    #         '0020000E']['QueryValue']).first()
    #     if series:
    #         # https://github.com/seperman/deepdiff
    #         # create instance
    #         meta_dict = DatabaseImporter.find_diff_dict(series.meta, meta)
    #         instance = DataEntityB(meta=meta_dict)
    #         DatabaseImporter.add_linker(instance, series, "DicomSeries2Instance")
    #         add_and_commit_to_session(instance)
    #         return instance
    #     study = DataEntityB.query. \
    #         filter(DataEntityB.meta['0020000D']['QueryValue'].astext == meta['0020000D']['QueryValue']).first()
    #     if study:
    #         #create series and instance
    #         series_and_instance_meta = DatabaseImporter.find_diff_dict(study.meta, meta)
    #         instance = DataEntityB(meta=series_and_instance_meta)
    #         DatabaseImporter.add_linker(instance, study, "DicomStudy2Series")
    #         add_and_commit_to_session(instance)
    #         return instance
    #     patient = DataEntityB.query. \
    #         filter(DataEntityB.meta['00100020']['QueryValue'].astext == meta[
    #         '00100020']['QueryValue']).first()
    #     if patient:
    #         study_series_instance_meta = DatabaseImporter.find_diff_dict(patient.meta, meta)
    #         instance = DataEntityB(meta=study_series_instance_meta)
    #         DatabaseImporter.add_linker(instance, patient, "DicomPatient2Study")
    #         add_and_commit_to_session(instance)
    #         return instance
    #     #new patient -> first instance contains complite meta
    #     entityB = DataEntityB(meta=meta)
    #     add_and_commit_to_session(entityB)
    #     return entityB


    @staticmethod
    def add_linker(source : DataEntityB, target : DataEntityB, type: str):
        # todo check exists
        linker = Link(source=source, target=target, type=type)
        add_and_commit_to_session(linker)


    @staticmethod
    def add_collection(dataentities : list, type : str, meta=None) -> Collection:
        # todo check exists
        entityB = DataEntityB(meta=meta)
        collection = Collection(collection_2_dataentity=dataentities, type=type, data_entityb=entityB)
        add_to_session(entityB)
        add_to_session(collection)
        return entityB


class Database:
    @staticmethod
    def commit_to_db():
        commit_to_db()

    @staticmethod
    def refresh():
        refresh()

    @staticmethod
    def setup_db(app):
        from datamodel.database.schema import schema
        app.add_url_rule(
            '/graphql',
            view_func=GraphQLView.as_view(
                'graphql',
                schema=schema,
                graphiql=True  # for having the GraphiQL interface
            ))

        init_db()

    @staticmethod
    def init_db():
        init_db()

    @staticmethod
    def session():
        return session






