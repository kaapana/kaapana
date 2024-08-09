from fastapi import APIRouter, Request
from ..proxy_request import proxy_request

router = APIRouter()


@router.post("/workitems", tags=["UPS-RS"])
async def create_work_item(request: Request):
    return await proxy_request(request, "/workitems", "POST")


@router.post("/workitems/{UPSInstance}", tags=["UPS-RS"])
async def update_work_item(UPSInstance: str, request: Request):
    return await proxy_request(request, f"/workitems/{UPSInstance}", "POST")


@router.get("/workitems", tags=["UPS-RS"])
async def search_work_items(request: Request):
    return await proxy_request(request, "/workitems", "GET")


@router.get("/workitems/{UPSInstance}", tags=["UPS-RS"])
async def retrieve_work_item(UPSInstance: str, request: Request):
    return await proxy_request(request, f"/workitems/{UPSInstance}", "GET")


@router.put("/workitems/{UPSInstance}/state", tags=["UPS-RS"])
async def change_work_item_state(UPSInstance: str, request: Request):
    return await proxy_request(request, f"/workitems/{UPSInstance}/state", "PUT")


@router.post("/workitems/{UPSInstance}/cancelrequest", tags=["UPS-RS"])
async def cancel_work_item(UPSInstance: str, request: Request):
    return await proxy_request(
        request, f"/workitems/{UPSInstance}/cancelrequest", "POST"
    )


@router.post("/workitems/{UPSInstance}/subscribers/{AETitle}", tags=["UPS-RS"])
async def create_subscription(UPSInstance: str, AETitle: str, request: Request):
    return await proxy_request(
        request, f"/workitems/{UPSInstance}/subscribers/{AETitle}", "POST"
    )


@router.post("/workitems/{UPSInstance}/subscribers/{AETitle}/suspend", tags=["UPS-RS"])
async def suspend_subscription(UPSInstance: str, AETitle: str, request: Request):
    return await proxy_request(
        request, f"/workitems/{UPSInstance}/subscribers/{AETitle}/suspend", "POST"
    )


@router.delete("/workitems/{UPSInstance}/subscribers/{AETitle}", tags=["UPS-RS"])
async def delete_subscription(UPSInstance: str, AETitle: str, request: Request):
    return await proxy_request(
        request, f"/workitems/{UPSInstance}/subscribers/{AETitle}", "DELETE"
    )


@router.get("/subscribers/{AETitle}", tags=["UPS-RS"])
async def open_subscription_channel(AETitle: str, request: Request):
    return await proxy_request(request, f"/subscribers/{AETitle}", "GET")
