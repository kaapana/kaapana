from typing import Literal

from pydantic import BaseModel


class DevLink(BaseModel):
    label: str
    path: str


class MenuEntry(BaseModel):
    type: Literal["entry"] = "entry"
    # route slug for /web/<section>/<id>; unique per (section, id)
    id: str
    label: str
    icon: str = ""
    path: str  # iframe src / link target; shell also feeds this to checkAuthR
    target: Literal["iframe", "tab"] = "iframe"
    # "path" = iframe src gets the /project/<short_id> prefix, "none" = project-agnostic
    project: Literal["path", "none"] = "none"
    default: bool = False
    order: int = 1000
    # path the shell polls for a count badge; camelCase to match the wire contract
    badgePath: str = ""
    # API-doc links the shell offers in dev mode
    devLinks: list[DevLink] = []


class MenuSection(BaseModel):
    type: Literal["section"] = "section"
    id: str
    label: str
    icon: str = ""
    order: int = 1000
    entries: list[MenuEntry]


class MenuResponse(BaseModel):
    items: list[
        MenuSection | MenuEntry
    ]  # pre-sorted; sections and top-level entries interleaved
