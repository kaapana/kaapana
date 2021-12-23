import enum
import json
from datamodel.database.model_raw import Dataset as DatasetModel
from datamodel.database.model import DataEntity
from .DataImporter import DatabaseImporter, Database
from datamodel.database.base import commit_to_db, add_to_session, init_db

class Dataset:
    @staticmethod
    def add_generated(name: str, set_entities: [DataEntity] = None, access: str = None,
                      unit: bool = False, query: str = None, meta: json = None):
        dataset: DatasetModel = DatasetModel.query.filter(
            DatasetModel.name == name).first()
        if dataset:
            is_added = DatabaseImporter.add_access(dataset.data_entity, keycloak_group=access)
            return dataset
        data_entity = DatabaseImporter.add_data_entity(keycloak_group=access)
        Database.refresh()
        dataset = DatasetModel(name=name,
                          data_entity=data_entity,
                          search_query=query,
                          set_entities=set_entities,
                          unit=unit,
                          generated=True,
                          meta=meta)
        # TODO: how to handle json_meta?? compare? sort? overwrite?...
        add_to_session(dataset)
        return dataset