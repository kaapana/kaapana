from __future__ import annotations

from enum import Enum
from typing import Any, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class QueryOp(str, Enum):
    EQ = "eq"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


class FilterNode(BaseModel):
    type: Literal["filter"] = "filter"
    field: str = Field(
        ...,
        description="Dotted path like 'id', 'storage.type', or 'metadata.acquisition.value'",
    )
    op: QueryOp
    value: Any


class GroupNode(BaseModel):
    type: Literal["group"] = "group"
    op: Literal["and", "or"] = "and"
    children: List["QueryNode"]


QueryNode = Union[FilterNode, GroupNode]


class QueryRequest(BaseModel):
    where: Optional[QueryNode] = Field(
        None,
        description="Root of the query tree. If omitted, all entities match.",
    )
    cursor: Optional[UUID] = Field(
        None,
        description="Return entities whose ID is greater than this cursor (exclusive).",
    )
    limit: int = Field(
        100,
        ge=1,
        le=10000,
        description="Maximum number of entities to return.",
    )


class QueryResponse(BaseModel):
    results: List["DataEntity"]
    next_cursor: Optional[UUID] = Field(
        None,
        description="Cursor to request the next page, or null if there are no more results.",
    )
    total_count: int = Field(
        ...,
        description="Total number of entities that match the query before pagination.",
    )


class QueryIndexRequest(BaseModel):
    where: Optional[QueryNode] = Field(
        None,
        description="Root of the query tree. If omitted, all entities match.",
    )
    cursor: Optional[UUID] = Field(
        None,
        description="Skip all entities up to and including this ID when streaming the ordered index.",
    )


from app.models.domain import DataEntity  # noqa: E402

QueryResponse.model_rebuild()
GroupNode.model_rebuild()
