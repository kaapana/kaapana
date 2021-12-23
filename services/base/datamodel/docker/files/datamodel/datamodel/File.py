import enum
import json
from datamodel.database.model_raw import File as FileModel
from datamodel.database.model import DataEntity
from .DataImporter import DatabaseImporter, Database
from datamodel.database.base import commit_to_db, add_to_session, init_db

class File:
    @staticmethod
    def add(path: str, location: str) -> FileModel:
        file: FileModel = FileModel.query.filter(FileModel.path == path and FileModel.location == location).first()
        if file:
            return file
        data_entity = DatabaseImporter.add_data_entity()
        file = FileModel(path=path, location=location, data_entity=data_entity)
        add_to_session(file)
        return file
