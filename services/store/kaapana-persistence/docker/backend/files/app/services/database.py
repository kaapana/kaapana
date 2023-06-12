from abc import ABC, abstractmethod
from typing import Tuple, NewType, Any
from dataclasses import dataclass, asdict

Identifier = NewType("Identifier", str)


class Database(ABC):
    @abstractmethod
    async def insert(self, object: Any, collection: str) -> Identifier:
        ...

    @abstractmethod
    async def update(
        self, identifier: Identifier, object: Any, collection: str
    ) -> Identifier:
        ...

    @abstractmethod
    async def delete(self, identifier: Identifier, collection: str):
        ...

    @abstractmethod
    async def query(self, query_obj, collection: str) -> Tuple[Identifier, Any]:
        ...

    @abstractmethod
    async def distinct(self, field: str, collection: str):
        ...

    @abstractmethod
    async def get(
        self, identifier: Identifier, collection: str
    ) -> Tuple[Identifier, Any]:
        ...

    async def list(self, collection: str) -> Tuple[Identifier, Any]:
        # TODO can we get rid of this?
        async for x in self.query({}, collection):
            yield x

    async def delete_query(self, query, collection: str):
        collection = self.collections.get(collection, {})
        items = self.query(query, collection)
        count = 0

        for idx, _ in items:
            self.delete(idx, collection)
            count += 1

        if count == 0:
            return None
        else:
            return count

    async def distinct(self, field: str, collection: str):
        collection = self.collections.get(collection, {})

        result = []
        for _, item in collection.items():
            result.append(item[field])

        for x in set(result):
            yield x


@dataclass
class CASObject:
    """Representation of the object as they are stored in the CAS"""

    collection: str
    object: Any


from app.services.cas import CAS
import json
import io


class CASBackedDatatbase(Database):
    def __init__(self, db: Database, cas: CAS):
        self.db = db
        self.cas = cas

    async def insert(self, object: Any, collection: str) -> Identifier:
        cas_object = CASObject(object=object, collection=collection)
        file = io.StringIO(json.dumps(asdict(cas_object)))
        self.cas.store(file)
        return self.db.insert(object, collection)

    async def update(
        self, identifier: Identifier, object: Any, collection: str
    ) -> Identifier:
        return self.db.update(identifier, object, collection)

    async def delete(self, identifier: Identifier, collection: str):
        # TODO search object in CAS and delete it
        return self.db.delete(identifier, collection)

    async def query(self, query_obj, collection: str) -> Tuple[Identifier, Any]:
        return self.db.query(query_obj, collection)

    async def distinct(self, field: str, collection: str):
        return self.db.distinct(field, collection)

    async def get(
        self, identifier: Identifier, collection: str
    ) -> Tuple[Identifier, Any]:
        return self.db.get(identifier, collection)

    async def list(self, collection: str) -> Tuple[Identifier, Any]:
        return self.db.list(collection)

    async def delete_query(self, query, collection: str):
        return self.db.delete_query(query, collection)

    async def distinct(self, field: str, collection: str):
        return self.db.distinct(field, collection)


from uuid import uuid1


class InMemoryDatabase(Database):
    def __init__(self):
        self.collections = {}

    async def insert(self, object: Any, collection: str) -> Identifier:
        col = self.collections.get(collection, {})
        idx = str(uuid1())
        col[idx] = object
        self.collections[collection] = col
        return idx

    async def update(
        self, identifier: Identifier, object: Any, collection: str
    ) -> Identifier:
        col = self.collections.get(collection, {})
        col[identifier] = object
        return identifier

    async def delete(self, identifier: Identifier, collection: str):
        collection = self.collections.get(collection, {})
        if identifier in collection:
            collection.pop(identifier)
            return 1
        else:
            return None

    async def get(self, identifier: Identifier, collection: str):
        # TODO Where is this used? can we generalize this
        collection = self.collections.get(collection, {})
        if identifier in collection:
            return (identifier, collection.get(identifier))
        else:
            return None

    async def query(self, query_obj, collection: str):
        collection = self.collections.get(collection, {})
        resultset = {}
        for idx, item in collection.items():
            match = True
            for key, value in query_obj.items():
                if key not in item:
                    match = False
                    break
                if item[key] != value:
                    match = False
                    break
            if match:
                resultset[idx] = item
        for idx, item in resultset.items():
            yield (idx, item)


from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


class MongoDatabase(Database):
    def __init__(self, mongodb_url: str, db: str):
        self.client = AsyncIOMotorClient(mongodb_url)
        self.db = self.client[db]

    async def insert(self, object, collection):
        result = await self.db[collection].insert_one(object)
        if not result:
            return None
        else:
            return str(result.inserted_id)

    async def update(
        self, identifier: Identifier, object: Any, collection: str
    ) -> Identifier:
        result = await self.db[collection].replace_one(
            {"_id": ObjectId(identifier)}, object
        )
        if result.modified_count == 1:
            return identifier
        else:
            return None

    async def delete(self, identifier: str, collection: str):
        res = await self.db[collection].delete_one({"_id": ObjectId(identifier)})
        if not res:
            return None
        else:
            return res.deleted_count

    async def delete_query(self, query, collection: str):
        res = await self.db[collection].delete_many(query)
        if not res:
            return None
        else:
            return res.deleted_count

    async def get(self, identifier: str, collection: str):
        # TODO Where is this used? can we generalize this
        async for doc in self.db[collection].find({"_id": ObjectId(identifier)}):
            idx = doc.pop("_id")
            return (str(idx), doc)

    async def query(self, query_obj, collection: str):
        async for doc in self.db[collection].find(query_obj):
            idx = doc.pop("_id")
            yield (str(idx), doc)

    async def distinct(self, field: str, collection: str):
        result = await self.db[collection].distinct("$id")
        for x in result:
            yield x


# import asyncio
# import asyncpg
# class PostgresDatabase(Database):
#     async def __init__(self, user: str, password, str, database: str, host: str):
#         self.conn = await asyncpg.connect(user=user, passsword=password, database=database, host=host)
