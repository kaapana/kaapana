"""Portal API entrypoint.

No request-level authorization is registered here on purpose: the service has
none of its own, so the gateway's `^/portal-api/.*` GET grant in auth-backend's
`data.rego` is the only gate on it. Whatever menu filtering a shell applies runs
in the browser and is therefore cosmetic, not a control.
"""

import logging

from fastapi import FastAPI

from app.api import router
from app.config import get_settings

logging.basicConfig(level=get_settings().LOG_LEVEL.upper())


def create_app() -> FastAPI:
    app = FastAPI(title="Portal API", version="0.0.1")

    app.include_router(router)

    @app.get("/health", summary="Health check")
    async def health_check() -> dict:
        # no k8s call: liveness must not flap with the API server
        return {"status": "ok"}

    return app


app = create_app()
