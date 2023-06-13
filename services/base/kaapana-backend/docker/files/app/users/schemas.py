from pydantic.dataclasses import dataclass


@dataclass
class KaapanaUser:
    idx: str
    name: str
    attributes: dict
    firstName: str
    lastName: str
    email: str


@dataclass
class KaapanaGroup:
    idx: str
    name: str


@dataclass
class KaapanaRole:
    idx: str
    name: str
    description: str
