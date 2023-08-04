import logging
import urnparse
import jsonschema
import re
import semver

from fastapi import HTTPException
from jsonschema_spec import Spec
from app.logger import get_logger, function_logger_factory
from app.services.schema import SchemaService
from app.services.database import Database

logger = get_logger(__name__, logging.DEBUG)


class ObjectService:
    def __init__(self, db: Database, schema_service: SchemaService):
        self.namespaces = {}
        self.db = db
        self.schema_service = schema_service

    def decompose_urn(self, obj_urn: str):
        # urn:kaapana:objects:{name}                      --> Schema (Latest Version)
        # urn:kaapana:objects:{name}:{version}            --> Schema
        # urn:kaapana:objects:{name}:{objectid}           --> Object (Latest Version)
        # urn:kaapana:objects:{name}:{objectid}:{version} --> Object
        try:
            urn_obj = urnparse.URN8141.from_string(obj_urn.lower())
            urn = str(urn_obj)
        except urnparse.InvalidURNFormatError as e:
            raise HTTPException(422, f"Invalid urn '{obj_urn}'")

        match = re.match(r"(urn:[^:]*:[^:]*)(:([^:]*))?(:([^:]*))?", urn)

        schema_urn = match.group(1)

        # urn:kaapanaobjects:{name}:{version}
        # urn:kaapanaobjects:{name}:{objectid}
        identifier = None
        schema_version = None
        if match.group(3):
            x = match.group(3)
            if "." in x:
                # Semver has dots
                schema_version = x
            else:
                # UUIDs and ObjectIds have no dots
                identifier = x

        if match.group(5):
            schema_version = match.group(5)

        return (schema_urn, schema_version, identifier)

    async def store(
        self, obj, urn: str, skip_validation: bool = False, override: bool = False
    ):
        """Stores a new object

        :param urn: Either a schema urn (if a new object should be created), or a existing object urn which is either updated (version exissts and override = true) or extendend by this version
        """
        (schema_urn, schema_version, identifier) = self.decompose_urn(urn)
        schema_query_urn = (
            f"{schema_urn}:{schema_version}" if schema_version else schema_urn
        )
        schemas = [x async for x in self.schema_service.get(schema_query_urn)]
        if len(schemas) != 1:
            raise HTTPException(404, f"Schema {schema_query_urn} does not exist!")
        schema = schemas[0]
        if not skip_validation:
            try:
                jsonschema.validate(obj, schema)
            except jsonschema.exceptions.ValidationError as e:
                raise HTTPException(422, f"Object does not match schema. {str(e)}")

        # Workaround since the database is not able to quer for objects with dot in field names
        version = schema["version"].replace(".", "_")

        if identifier:
            (_, parent) = await self.db.get(identifier, schema_urn)
            if parent:
                if version in parent:
                    if override:
                        # Override existing version of the object
                        parent[version] = obj
                    else:
                        raise HTTPException(
                            409,
                            "An object with this identifer exist already in this version version!",
                        )
                else:
                    # Object exist but new version was posted
                    parent[version] = obj
            else:
                # Object with given Identifier was not foudn
                raise HTTPException(404, "Referenced object does not exist")
            idx = await self.db.update(identifier, parent, schema_urn)
        else:
            # No identifier given, create a new object
            idx = await self.db.insert({version: obj}, schema_urn)

        if not idx:
            raise Exception("Something went wrong during insert")
        return f"{schema['$id']}:{idx}:{schema['version']}"

    async def delete(self, urn: str, all_versions: bool = False):
        (schema_urn, schema_version, identifier) = self.decompose_urn(urn)

        schema_query_urn = (
            f"{schema_urn}:{schema_version}" if schema_version else schema_urn
        )
        schemas = [x async for x in self.schema_service.get(schema_query_urn)]
        if len(schemas) != 1:
            raise HTTPException(404, f"Schema {schema_query_urn} does not exist!")
        schema = schemas[0]

        if not identifier:
            raise HTTPException(
                404, f"Cannot delete object without identifier in urn: {obj_urn}"
            )

        if all_versions:
            return await self.db.delete(identifier, schema_urn)
        else:
            obj = await self.db.get(identifier, schema_urn)
            if not obj:
                raise HTTPException(
                    404,
                    f"Object with id:{identifier} does not exist for schema {schema_urn}",
                )

            # Workaround since the database is not able to quer for objects with dot in field names
            version = schema["version"].replace(".", "_")
            if version not in obj:
                raise HTTPException(
                    404,
                    f"Object with id:{identifier} for schema {schema_urn} does not have a version {schema['version']}",
                )
            obj.pop(version)
            return await self.db.update(identifier, obj, schema_urn)

    async def get(self, urn: str):
        (schema_urn, schema_version, identifier) = self.decompose_urn(urn)

        if not identifier:
            # Schema URN --> Return all objects
            async for (idx, obj) in self.db.list(schema_urn):
                yield schema_urn + ":" + idx
        else:
            ret = await self.db.get(identifier, schema_urn)
            if not ret:
                raise HTTPException(404, f"Object {urn} was not found")
            (idx, doc) = ret

            if schema_version:
                # Workaround since the database is not able to quer for objects with dot in field names
                version = schema_version.replace(".", "_")
                if not version in doc:
                    raise HTTPException(404, "Object was not found in specific version")
            else:
                # return latest version if version is not specified
                schema_version = sorted(
                    (x.replace("_", ".") for x in doc.keys()),
                    key=lambda x: semver.Version.parse(x),
                )[-1]
                version = schema_version.replace(".", "_")

            yield (schema_urn + ":" + idx + ":" + schema_version, doc[version])

    async def query(self, urn: str, query_object):
        (schema_urn, schema_version, identifier) = self.decompose_urn(urn)

        schema_query_urn = (
            f"{schema_urn}:{schema_version}" if schema_version else schema_urn
        )
        schemas = [x async for x in self.schema_service.get(schema_query_urn)]
        if len(schemas) != 1:
            raise HTTPException(404, f"Schema {schema_query_urn} does not exist!")
        schema = schemas[0]

        for k, v in query_object.items():
            if v.isnumeric():
                query_object[k] = int(v)
            elif v.lower() == "false":
                query_object[k] = False
            elif v.lower() == "true":
                query_object[k] = True

        # TODO query is only executed on latest version

        version = schema["version"].replace(".", "_")
        new_query_object = {
            f"{version}.{key}": value for (key, value) in query_object.items()
        }
        print(new_query_object)
        async for (idx, doc) in self.db.query(new_query_object, schema_urn):
            yield (schema_urn + ":" + str(idx), doc)
