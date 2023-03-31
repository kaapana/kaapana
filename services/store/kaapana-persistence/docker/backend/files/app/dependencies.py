import os
from functools import lru_cache
from app.services.schema import SchemaService
from app.services.object import ObjectService
from app.services.cas import CAS
from app.services.urn_dispatcher import (
    URNDispatcher,
    ExternalHTTPServiceResolver,
    PersistenceLayerResolver,
    CASResolver,
)
from app.services.database import Database, MongoDatabase, InMemoryDatabase
from app.config import get_settings


@lru_cache
def get_cas() -> CAS:
    settings = get_settings()
    return CAS(settings.cas_root_path)


@lru_cache()
def get_db() -> Database:
    settings = get_settings()
    return MongoDatabase(settings.mongodb_url, settings.mongodb_db)
    # return InMemoryDatabase()


@lru_cache()
def get_schema_service() -> SchemaService:
    return SchemaService(get_db())


@lru_cache
def get_object_service() -> ObjectService:
    return ObjectService(get_db(), get_schema_service())


@lru_cache
def get_dispatcher_service() -> URNDispatcher:
    settings = get_settings()
    dispatcher = URNDispatcher()
    dispatcher.add_resolver(
        ExternalHTTPServiceResolver(
            "urn:kaapana:meta:(.+)",
            settings.os_base_url + "/meta-index/_doc/{{RESSOURCE}}",
            description="Resolves resources stored in opensearch",
        )
    )
    dispatcher.add_resolver(
        ExternalHTTPServiceResolver(
            "urn:kaapana:dicom:study:(.+)",
            settings.quido_base_url + "/KAAPANA/rs/studies/{{RESSOURCE}}/series",
            viewer_template=settings.ohif_viewer + "/{{RESSOURCE}}"
            if settings.ohif_viewer
            else None,
            description="Resolves dicom studies to dicom json resources",
        )
    )
    dispatcher.add_resolver(CASResolver(get_cas()))
    dispatcher.add_resolver(
        PersistenceLayerResolver(get_object_service(), get_schema_service())
    )
    return dispatcher
