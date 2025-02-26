from app.database.queries import verify_postgres_conn
from app.websockets import ConnectionManager, get_connection_manager
from fastapi import APIRouter, Depends, HTTPException
from fastapi_versioning import version

router = APIRouter()


@router.get("/check-db-connection", tags=["Health"])
@version(1)
async def check_db_connection():
    verified, err = await verify_postgres_conn()
    if verified:
        return {"status": "Database connection successful"}
    else:
        raise HTTPException(
            status_code=500, detail=f"Database connection failed, {err}"
        )


@router.get("/active-connections", tags=["Health"])
@version(1)
async def check_active_websocket_connection(
    con_mgr: ConnectionManager = Depends(get_connection_manager),
):
    return {"status": "active", "active_connections": len(con_mgr.active_connections)}
