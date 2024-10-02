from fastapi import APIRouter, Request, Response

router = APIRouter()


@router.get("/studies", tags=["QIDO-RS"])
async def query_studies(request: Request):
    return Response(status_code=200, content="Test")


@router.get("/somethingelse")
def try_it():
    pass
