from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, get_async_db
from app.models.query import QueryIndexRequest, QueryRequest, QueryResponse
from app.services.entity_query import (
    QueryTranslationError,
    execute_entity_query,
    prepare_query_index_statement,
)

router = APIRouter(prefix="/entities", tags=["entity-queries"])


@router.post("/query", response_model=QueryResponse, summary="Query data entities")
async def query_entities(
    request: QueryRequest, db: AsyncSession = Depends(get_async_db)
) -> QueryResponse:
    try:
        results, total_count, next_cursor = await execute_entity_query(db, request)
    except QueryTranslationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return QueryResponse(
        results=results, next_cursor=next_cursor, total_count=total_count
    )


@router.post(
    "/query/index",
    response_class=StreamingResponse,
    summary="Stream IDs that match a query",
    description="Returns the full ordered list of entity IDs that match the provided query filter, allowing clients to hydrate large result sets without issuing thousands of cursor requests.",
)
async def stream_query_index(
    request: QueryIndexRequest, db: AsyncSession = Depends(get_async_db)
) -> StreamingResponse:
    try:
        total_count, stmt = await prepare_query_index_statement(db, request)
    except QueryTranslationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def iterator() -> AsyncIterator[bytes]:
        yield b'{"total_count":' + str(total_count).encode() + b',"items":['
        first = True
        async with AsyncSessionLocal() as stream_session:
            result = await stream_session.stream(stmt)
            try:
                async for entity_id in result.scalars():
                    prefix = b"" if first else b","
                    first = False
                    yield prefix + f'"{entity_id}"'.encode()
            finally:
                await result.close()
        yield b'],"next_cursor":null}'

    return StreamingResponse(iterator(), media_type="application/json")
