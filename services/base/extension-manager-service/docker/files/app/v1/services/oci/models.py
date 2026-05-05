from pydantic import BaseModel


class Extension(BaseModel):
    name: str
    version: str
    description: str


class Registry(BaseModel):
    registry: str
    repository: str
    extensions: list[Extension]
