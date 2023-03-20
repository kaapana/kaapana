from typing import Generic, TypeVar
from pydantic.generics import GenericModel

ResponseType = TypeVar("ResponseType")


class Response(GenericModel, Generic[ResponseType]):
    data: ResponseType
    # additional properties here could be used to inject an optional error or other information into every response
