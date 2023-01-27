from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.routing import Mount as Mount 

from security_app import router as security_app_router

#app = FastAPI(root_path=os.getenv('APPLICATION_ROOT', '/security'))

#todo: json persistence of data
app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
	#logging.error(f"{request}: {exc_str}")
    print(f"{request}: {exc_str}")
    content = {'status_code': 10422, 'message': exc_str, 'data': None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

app.mount("/security", security_app_router)
