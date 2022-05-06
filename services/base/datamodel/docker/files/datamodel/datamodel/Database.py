from datamodel.database.base import commit_to_db, add_to_session, init_db, refresh, session, add_and_commit_to_session
from datamodel.database.modelB import DataEntityB, Collection, Link
from strawberry.fastapi import GraphQLRouter

class DatabaseImporter:
    @staticmethod
    def add_entityB(meta: dict) -> DataEntityB:
        entity: DataEntityB = DataEntityB.query \
                     .filter(DataEntityB.meta['hash_id'].astext == meta['hash_id']).first()
        if entity:
            return entity
        #use specifc encoder
        #meta_json = json.dumps(meta, indent=2, cls=ComplexEncoder).encode("utf-8")
        entity = DataEntityB(meta=meta)
        add_and_commit_to_session(entity)
        return entity

    @staticmethod
    def add_linker(source : DataEntityB, target : DataEntityB, type: str):
        # todo check exists
        linker: Link = Link.query.filter(Link.source == source, Link.target == target, Link.type == type).first()
        if linker:
            return linker

        linker = Link(source=source, target=target, type=type)
        add_and_commit_to_session(linker)
        return linker


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
        graphql_app = GraphQLRouter(schema)

        app.include_router(graphql_app, prefix="/graphql")
        init_db()

    @staticmethod
    def init_db():
        init_db()

    @staticmethod
    def session():
        return session






