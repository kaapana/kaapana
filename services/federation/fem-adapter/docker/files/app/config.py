from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Runtime configuration for fem-adapter, read entirely from the environment
    so the same image works unmodified in docker-compose and in the Helm chart.
    """

    # Base URL of the Kaapana workflow-api, including its version prefix,
    # e.g. "http://api:8080/v1" in the local dev sandbox.
    WORKFLOW_API_BASE_URL: str = "http://workflow-api:8080/v1"

    # Kaapana project used to create workflow runs. workflow-api's
    # POST /v1/workflow-runs reads this from a "Project" cookie
    # (URL-encoded JSON with an "id" key) rather than a request body field.
    PROJECT_ID: str = "fem-sandbox"

    # workflow_engine assigned to every Workflow this adapter creates.
    # "dummy" selects workflow-api's built-in DummyAdapter, which fakes a
    # workflow engine so no real Airflow is needed for local testing.
    WORKFLOW_ENGINE: str = "dummy"

    # How long / how often to poll workflow-api for a terminal
    # WorkflowRunStatus before answering the FEM-client's submit_run call.
    POLL_INTERVAL_SECONDS: float = 1.0
    POLL_TIMEOUT_SECONDS: float = 15.0

    # Sandbox-only convenience: DummyAdapter.get_workflow_run_status() falls
    # back to always returning RUNNING unless a test explicitly overrides it
    # via workflow-api's /v1/adapter-test/set-status endpoint (gated behind
    # ENABLE_TEST_ADAPTER=true on workflow-api). When this flag is set, and
    # the workflow uses the "dummy" engine, fem-adapter calls that endpoint
    # itself once the run has been picked up by the engine, so a local
    # end-to-end test can observe a real terminal status without a human
    # (or a real workflow engine) in the loop. Never enable this against a
    # real workflow engine adapter.
    DUMMY_ENGINE_AUTOCOMPLETE: bool = False

    model_config = SettingsConfigDict(env_prefix="FEM_ADAPTER_")


settings = Settings()
