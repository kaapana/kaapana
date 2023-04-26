import re

from abc import ABC, abstractmethod
from fastapi import HTTPException
from typing import Any, List

from app.logger import get_logger

logger = get_logger(__name__)


class URNResolver(ABC):
    def __init__(self, description: str = ""):
        self.description = description
        super().__init__()

    @abstractmethod
    async def can_handle(self, urn: str) -> bool:
        ...

    async def get_viewer_link(self, urn: str) -> str:
        return None

    async def get(self, urn: str) -> Any:
        raise HTTPException(501)

    async def put(self, urn: str, data) -> Any:
        raise HTTPException(501)

    async def delete(self, urn: str) -> Any:
        raise HTTPException(501)


import httpx
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask


class ExternalHTTPServiceResolver(URNResolver):
    TEMPLATE_RESOURCE_IDENTIFIER = "{{RESSOURCE}}"

    def __init__(
        self,
        urn_regex: str,
        url_template: str,
        viewer_template: str = None,
        get_allowed: bool = True,
        put_allowed: bool = True,
        delete_allowed: bool = True,
        description: str = "",
    ):
        """Resolves a urn to an external http request

        :param urn_regex: Regex matching your urn (used to see if this instance can answer request)
            wich also contains a single group to identifiy the resource identifier to fill in the url_template
        :param url_template: a url containing {{RESSOURCE}} which is used as template for urn2url transaltion
        """
        self.urn_regex = urn_regex
        self.url_template = url_template
        self.viewer_template = viewer_template
        self.get_allowed = get_allowed
        self.put_allowed = put_allowed
        self.delete_allowed = delete_allowed
        super().__init__(description=description)

    async def can_handle(self, urn: str) -> bool:
        return True if re.match(self.urn_regex, urn) else False

    async def get_viewer_link(self, urn: str) -> str:
        if self.viewer_template:
            return str(await self._urn2url(urn, template=self.viewer_template))
        else:
            return await super().get_viewer_link(urn)

    async def _urn2url(self, urn: str, template=None) -> httpx.URL:
        match = re.match(self.urn_regex, urn)
        if not match:
            raise Exception("Can not resolve requested urn {urn}")
        ressource = match.group(1)
        if not ressource:
            raise Exception(
                f"Could not determin ressource form urn {urn} with regex {self.urn_regex}"
            )

        if not template:
            template = self.url_template

        url_str = template.replace(self.TEMPLATE_RESOURCE_IDENTIFIER, ressource)
        return httpx.URL(
            url_str
        )  # path=request.url.path, query=request.url.query.encode("utf-8"))

    async def _http_request(self, url: httpx.URL, method: str, data=None):
        logger.info("Relay request to {url} (base_url = {self.base_url})")
        client = httpx.AsyncClient()
        rp_req = client.build_request(
            method,
            url,  # headers=request.headers.raw, content=await request.body()
            data=data,
        )
        try:
            rp_resp = await client.send(rp_req, stream=True)
            return StreamingResponse(
                rp_resp.aiter_raw(),
                status_code=rp_resp.status_code,
                headers=rp_resp.headers,
                background=BackgroundTask(rp_resp.aclose),
            )
        except httpx.ConnectError as e:
            raise HTTPException(
                503, f"Could not connect to {e.request.url} becasue {e}"
            )

    async def get(self, urn: str) -> Any:
        if not self.get_allowed:
            raise HTTPException(501)
        return await self._http_request(await self._urn2url(urn), "GET")

    async def put(self, urn: str, data) -> Any:
        if not self.put_allowed:
            raise HTTPException(501)
        return await self._http_request(await self._urn2url(urn), "PUT", data)

    async def delete(self, urn: str) -> Any:
        if not self.delete_allowed:
            raise HTTPException(501)
        return await self._http_request(await self._urn2url(urn), "DELETE")


from app.services.object import ObjectService
from app.services.schema import SchemaService


class PersistenceLayerResolver(URNResolver):
    def __init__(self, object_service: ObjectService, schema_service: SchemaService):
        self.object_service = object_service
        self.schema_service = schema_service
        super().__init__("Resolves objects to internal persistence layer")

    async def can_handle(self, urn: str) -> bool:
        return urn.startswith("urn:kaapana")

    async def get(self, urn: str) -> Any:
        (schema_urn, schema_version, identifier) = self.object_service.decompose_urn(
            urn
        )
        if identifier:
            obj = [x async for x in self.object_service.get(urn)]
            if obj:
                # TODO this is very messy
                if type(obj[0]) != str:
                    (_, doc) = obj[0]
                    return doc
        else:
            async for schema in self.schema_service.get(urn, False):
                return schema
        raise HTTPException(404)

    async def put(self, urn: str, data) -> Any:
        # TODO integrate schema service
        return self.object_service.store(data, urn)

    async def delete(self, urn: str) -> Any:
        # TODO integrate schema service
        return self.object_service.delete(urn)


from app.services.cas import CAS


# TODO replacable by internal redirect?
class CASResolver(URNResolver):
    PREFIX: str = "urn:kaapana:cas:"

    def __init__(self, cas: CAS):
        self.cas = cas
        super().__init__("Resolves objects to internal cas")

    async def can_handle(self, urn: str) -> bool:
        return urn.startswith(self.PREFIX)

    async def get(self, urn: str) -> Any:
        return await self.cas.get(urn.replace(self.PREFIX, ""))

    async def put(self, urn: str, data) -> Any:
        # TODO
        raise HTTPException(501)

    async def delete(self, urn: str) -> Any:
        # TODO
        raise HTTPException(501)


class URNDispatcher:
    def __init__(self):
        self.resolvers = []

    def add_resolver(self, resolver: URNResolver):
        self.resolvers.append(resolver)

    async def dispatch(self, urn: str) -> URNResolver:
        for resolver in self.resolvers:
            if await resolver.can_handle(urn):
                return resolver
        raise HTTPException(404, "No resolver capable of resolving {urn} found!")

    async def get(self, urn: str):
        resolver = await self.dispatch(urn)
        return await resolver.get(urn)

    async def get_viewer_link(self, urn):
        resolver = await self.dispatch(urn)
        return await resolver.get_viewer_link(urn)

    async def put(self, urn: str, data):
        resolver = await self.dispatch(urn)
        return await resolver.put(urn, data)

    async def delete(self, urn: str):
        resolver = await self.dispatch(urn)
        return await resolver.delte(urn)
