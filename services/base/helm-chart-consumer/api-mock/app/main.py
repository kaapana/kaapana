from fastapi import FastAPI

from .routers import applications, projects, releases

DESCRIPTION = """\
This is a proposal for the API of the Helm Chart Consumer. Every route returns fixed example data
and changes nothing.

The Helm Chart Consumer registers the helm-chart contents of installed extensions and deploys,
updates and undeploys them as applications, in a project or platform-wide. Each deployed
application is one helm release, which this API calls a release.

Kaapana's gateway authenticates every request and passes the user and their roles in headers.
The Helm Chart Consumer decides from these roles what each caller may do:

- Scientists open the releases of their projects and all platform-wide releases and see their
  status and configuration. They also report when they finish the work in a release that a
  workflow started.
- Principal investigators also deploy, update and undeploy in their projects.
- Kaapana-system-admins may do everything, and only they deploy platform-wide and enable
  applications in projects.
- The Extension Manager calls the registration routes from inside the cluster.

Errors have the body `{"detail": "<message>"}`. A request that is well-formed but rejected for its
content answers 400. Only a malformed request answers 422, and its `detail` is a list of validation
errors instead.
"""

app = FastAPI(
    title="Helm Chart Consumer API (mock)",
    version="0.1.0",
    description=DESCRIPTION,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

for router in (applications.router, releases.router, projects.router):
    app.include_router(router, prefix="/v1")


@app.get("/v1/health", tags=["Health"])
def health() -> dict[str, str]:
    """Report that the service is up."""
    return {"status": "ok"}
