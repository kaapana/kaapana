import urnparse
import logging
import semver
import re

from jsonschema_spec import Spec
from fastapi import HTTPException
from deepdiff import DeepDiff
from app.services.database import Database

from app.logger import get_logger, function_logger_factory

logger = get_logger(__name__, logging.DEBUG)


class SchemaService:
    def __init__(self, db: Database, schemas_collection: str = "schemas"):
        self.db = db
        self.schemas_collection = schemas_collection

    async def list(self, include_version: bool = False):
        if not include_version:
            async for urn in self.db.distinct("$id", self.schemas_collection):
                yield urn
        else:
            async for (idx, doc) in self.db.list(self.schemas_collection):
                yield f"{doc['$id']}:{doc['version']}"

    async def register(self, schema_dict, exist_ok: bool = True):
        # TODO if the added version is newer than the existing one return only urn without version, if it is older return it with version
        # Step 0 - Normalization
        if "$id" in schema_dict:
            schema_dict["$id"] = schema_dict["$id"].lower()

        if "version" in schema_dict:
            schema_dict["version"] = schema_dict["version"].lower()

        # Step 1 - Validate schema_dict
        schema = Spec.from_dict(schema_dict)
        if "$id" not in schema:
            raise HTTPException(422, f"Schema has no $id field")

        if "version" not in schema:
            raise HTTPException(422, f"Schema has no 'version' field")
        try:
            version = semver.Version.parse(schema["version"])
        except ValueError as e:
            raise HTTPException(
                422,
                f"Schema version '{schema['version']}' is not a valid SemVer version",
            )

        # Step 2 - Validate URN
        try:
            urn_obj = urnparse.URN8141.from_string(schema["$id"])
            urn = str(urn_obj)
        except urnparse.InvalidURNFormatError as e:
            raise HTTPException(422, f"Invalid urn $id:'{schema['$id']}'")

        # Step 3 - Check if Schema already exists
        # doc = await self.schemas.find_one({"$id": urn})
        # doc = await self.schemas.find_one({"$id": urn, "version": str(version)})
        docs = [
            doc
            async for doc in self.db.query(
                {"$id": urn, "version": str(version)}, self.schemas_collection
            )
        ]
        if docs:
            existing_schema = Spec.from_dict(docs[0])
            # TODO Deep Diff does not work properly
            diff = DeepDiff(schema, existing_schema, ignore_order=True)
            if exist_ok:
                if diff:
                    raise HTTPException(
                        409,
                        f"Schema with urn {urn} already exist but differs diff {diff.to_json()}",
                    )
                return urn
            else:
                raise HTTPException(409, f"Schema with $id:'{urn}' already exists")
        else:
            logger.debug("Adding Schema $id=%s to database", urn)
            idx = await self.db.insert(schema_dict, self.schemas_collection)
            logger.info("Created new Schema $id=%s (doc id = %s)", urn, idx)

        return urn

    async def check_urn(self, urn: str):
        # urn should macht urn:kaapana:datatype:semver (e.g. urn:kaapana:Instance.semver)
        try:
            urn_obj = urnparse.URN8141.from_string(urn.lower())
            urn = str(urn_obj)
        except urnparse.InvalidURNFormatError as e:
            raise HTTPException(422, f"Invalid urn '{urn}'")

        match = re.match(r"(urn:[^:]*:[^:]*)(:(.*))?", urn)
        base_urn = match.group(1)
        if len(match.groups()) > 2:
            version = match.group(3)
        else:
            version = None
        return (base_urn, version)

    async def versions(self, urn: str):
        (urn, version) = await self.check_urn(urn)

        if version:
            docs = self.db.query(
                {"$id": urn, "version": version}, self.schemas_collection
            )
        else:
            docs = self.db.query({"$id": urn}, self.schemas_collection)

        async for (idx, doc) in docs:
            yield doc["version"]

    async def delete(self, urn: str) -> int:
        (urn, version) = await self.check_urn(urn)

        if not version:
            deleted_count = await self.db.delete_query(
                {"$id": urn}, self.schemas_collection
            )
        else:
            deleted_count = await self.db.delete_query(
                {"$id": urn, "version": version}, self.schemas_collection
            )

        if not deleted_count:
            return None
        else:
            return deleted_count

    async def latest_version(self, urn: str):
        (urn, version) = await self.check_urn(urn)
        if version:
            return version
        else:
            docs = self.db.query({"$id": urn}, self.schemas_collection)
            docs = sorted(
                [x async for (_, x) in docs],
                key=lambda doc: semver.Version.parse(doc["version"]),
            )
            if not docs:
                return None
            latest = docs[-1]
            return latest["version"]

    async def get(self, urn: str, all_versions: bool = False):
        (urn, version) = await self.check_urn(urn)

        if not version:
            docs = self.db.query({"$id": urn}, self.schemas_collection)
            docs = sorted(
                [x async for (_, x) in docs],
                key=lambda doc: semver.Version.parse(doc["version"]),
            )
            if len(docs) == 0:
                return

            if all_versions:
                for doc in docs:
                    yield doc
            else:
                latest = docs[-1]
                yield latest
        else:
            async for (idx, doc) in self.db.query(
                {"$id": urn, "version": version}, self.schemas_collection
            ):
                yield doc

    async def generate(self, urn: str, count: int):
        # TODO: If defs are not defined before they are used the generation does not work
        versions = [x async for x in self.get(urn)]
        if len(versions) != 1:
            raise HTTPException(404, f"Scheam {urn} does not exist!")
        schema = versions[0]

        from jsf import JSF

        faker = JSF(schema)
        return faker.generate(count)
