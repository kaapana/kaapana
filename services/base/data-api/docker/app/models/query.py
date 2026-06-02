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
    HAS_KEY = "has_key"


class FilterNode(BaseModel):
    type: Literal["filter"] = "filter"
    field: str = Field(
        ...,
        description="Dotted path like 'id', 'storage.type', or 'metadata.acquisition.value'",
    )
    op: QueryOp
    value: Any = Field(
        None,
        description="Operand for the operator. Omitted for presence ops like 'has_key'.",
    )


class GroupNode(BaseModel):
    type: Literal["group"] = "group"
    op: Literal["and", "or"] = "and"
    children: List["QueryNode"]


QueryNode = Union[FilterNode, GroupNode]


class SortSpec(BaseModel):
    """Single-key sort for a paged entity query.

    ``field`` reuses the filter dotted-path convention: ``created_at``, ``id``,
    or ``metadata.<key>[.<dot.path>]``. ``created_at``/``id`` use the existing
    index (cheap, any table size). A ``metadata.*`` path sorts the
    constraint-narrowed set with a type cast inferred from the registered schema
    (text fallback); it is capped by ``MAX_SORT_RESULT_SIZE`` to bound its cost.
    """

    field: str = Field(
        ...,
        description="Dotted path to sort by: 'created_at', 'id', or 'metadata.<key>[.<dot.path>]'.",
    )
    direction: Literal["asc", "desc"] = Field(
        "asc", description="Sort direction. NULLs always sort last."
    )


class QueryRequest(BaseModel):
    where: Optional[QueryNode] = Field(
        None,
        description="Root of the query tree. If omitted, all entities match.",
    )
    cursor: Optional[UUID] = Field(
        None,
        description="Return entities whose ID is greater than this cursor (exclusive).",
    )
    sort: Optional[SortSpec] = Field(
        None,
        description="Sort key. Omitted ⇒ ascending creation order (created_at, id) — the default.",
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


class EnsureEntityRequest(BaseModel):
    """Atomic get-or-create: create ``entity`` only if nothing matches ``where``.

    Generic over entity type — the ``where`` query expresses the identifying
    "these properties" (no dedicated identity column lives on the row). The first
    caller is dataset creation in the incoming-DICOM DAG; any per-identity object
    (a model, a cohort, a per-project singleton) dedups the same way.
    """

    where: "QueryNode" = Field(
        ...,
        description="Match query (same DSL as /entities/query). If any entity matches, it is returned instead of creating.",
    )
    entity: "DataEntity" = Field(
        ...,
        description="Entity to create verbatim if nothing matches. Its id should be a fresh UUID (discarded when an existing match wins).",
    )


class EnsureEntityResponse(BaseModel):
    created: bool = Field(
        ...,
        description="True if ``entity`` was inserted; False if an existing match was returned.",
    )
    entity: "DataEntity" = Field(
        ..., description="The created entity, or the pre-existing match."
    )


from app.models.domain import DataEntity  # noqa: E402

QueryResponse.model_rebuild()
GroupNode.model_rebuild()
EnsureEntityRequest.model_rebuild()
EnsureEntityResponse.model_rebuild()
