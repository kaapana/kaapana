# Workflow Service

## Motivation
One key feature of Kaapana is the execution of **Workflows**.  
A workflow consists of multiple steps (tasks) that may depend on each other, such as data retrieval, preprocessing, processing, post-processing, and result persistence.  

There exist several **Workflow Engines** (e.g., Airflow, Kubeflow, Argo Workflows) that help design workflows, schedule workflow runs, and monitor their state.  
Kaapana aims to be **agnostic** to specific engines. A workflow simply corresponds to a **workflow definition** interpretable by your engine of choice (e.g., a DAG file for Airflow).
Therefore Kaapana provides a **unified REST API** as a proxy to the authorities (i.e. external engines) that supports an exclusive list of commonly required actions when managing workflows and their execution:  
- **Posting workflows**  
- **Configuring workflow execution**  
- **Retrieving lifecycle information on workflow runs and task runs**  
- **Posting lifecycle events manually** (e.g., `CANCELED`, `RETRY`)  
- **Retrieving logs of task runs**  

This unified interface gives a **clear separation of concerns** and keeps the code base **clean and focused**.  

---

## Architecture

### High-Level Overview
The Workflow API follows a layered architecture:

```
Client → API router (HTTP) → Service → CRUD → DB
                           ↘ Engine Adapter → Workflow Engine
```

- **API layer (`app/api/`)**  
  - HTTP Routers for workflows and workflow runs.
  - Business logic for workflow and workflow run services.
  - Request validation and response serialization using Pydantic schemas.
  - Orchestrates database operations and adapter calls.

- **CRUD layer (`app/crud.py`)**  
  - Encapsulates SQLAlchemy queries.  
  - Provides all CRUD operations for workflows, tasks, workflow runs, and task runs.  
  - Returns ORM objects

- **Adapter layer (`app/adapters/`)**  
  - Bridges between the API and external workflow engines.
  - Each engine implements the `WorkflowEngineAdapter` interface.
  - Example: `DummyAdapter` (stub for testing)

- **Models and Schemas**  
  - **Models (`models.py`)** = SQLAlchemy ORM entities (DB persistence).  
  - **Schemas (`schemas.py`)** = Pydantic models for API validation and responses.  

```
files/
 ├── app/
 │   ├── api/           # FastAPI endpoints (HTTP layer)
 │   ├── adapters/      # Engine adapters (external integrations)
 │   ├── crud.py        # Database operations (repository layer)
 │   ├── models.py      # SQLAlchemy ORM models
 │   ├── schemas.py     # Pydantic request/response schemas
 │   ├── database.py    # DB session management
 │   ├── main.py        # FastAPI app entrypoint
 │   └── ...
 ├── tests/             # Integration tests
 ├── alembic/           # Database migrations
```

### Workflow Engine Adapter
The adapter is responsible for all communication with external engines:  
- Submitting workflows.  
- Validating workflow definitions.  
- Scheduling workflow runs.  
- Fetching state of workflows and task runs.  
- Cancelling or retrying executions.  

#### Adapter Interface (simplified)
```python
class WorkflowEngineAdapter(ABC):
    async def submit_workflow_revision(self, revision: WorkflowRevision) -> WorkflowRevision: ...
    async def get_workflow_tasks(self, revision: WorkflowRevision | WorkflowRef) -> list[TaskCreate]: ...
    async def submit_workflow_run(self, run: WorkflowRun, project_id: str) -> WorkflowRunUpdate: ...
    async def get_workflow_run_status(self, external_id: str) -> WorkflowRunStatus: ...
    async def cancel_workflow_run(self, external_id: str) -> WorkflowRunStatus: ...
    async def retry_workflow_run(self, external_id: str) -> WorkflowRunStatus: ...
    async def get_task_run_logs(self, external_id: str) -> str: ...
```

---

## Database Relations
* **Workflow** (stable identity: `id`, `title`, `workflow_engine`, `removed`)
    * `Workflow 1 — n WorkflowRevision` (append-only revision history).
    * `title` is unique among active workflows (partial index `WHERE removed = false`).

* **WorkflowRevision** (per-increment snapshot of `definition`, `workflow_parameters`, `labels`)
    * `WorkflowRevision n — 1 Workflow`.
    * `WorkflowRevision 1 — n Task` (tasks belong to a specific revision).
    * `WorkflowRevision 1 — n WorkflowRun` (runs pin to the revision they were submitted under).
    * `WorkflowRevision m — n Label` (via `workflow_revision_label`).
    * `UNIQUE(workflow_id, increment)`.

* **WorkflowRun**
    * `WorkflowRun n — 1 WorkflowRevision`.
    * `WorkflowRun m — n Label` (via `workflowrun_label`).
    * `WorkflowRun 1 — n TaskRun`.

* **Task**
    * `Task n — 1 WorkflowRevision`.
    * `Task 1 — n TaskRun`.
    * `Task m — n Task` (via `DownstreamTask`, dependency graph).

* **TaskRun**
    * `TaskRun n — 1 Task`.
    * `TaskRun n — 1 WorkflowRun`.

* **Label**
    * `Label m — n WorkflowRevision`.
    * `Label m — n WorkflowRun`.

---

## Workflow Execution & Syncing

### Inline execution
- On workflow creation (or any PATCH that bumps the increment):
  1. Workflow and its new revision are persisted in DB.
  2. Adapter submits the revision to the engine (`submit_workflow_revision`).
  3. Tasks are parsed from the engine in the background and persisted against the revision.

### Lazy evaluation
- On fetching a workflow run (`GET /workflow-runs/{id}`):  
  - If run state is **final** (`COMPLETED`, `FAILED`, `CANCELLED`) → return DB value.  
  - If run state is **active** → fetch fresh state from engine via adapter, update DB, return updated value.  

### Periodic sync
- A cron job runs periodically:  
  1. Selects all workflow runs with status != `COMPLETED`.  
  2. Queries engine via adapter for latest status.  
  3. Updates DB with current workflow and task run states.  

This ensures eventual consistency even if inline updates fail.  

---

## Design Decisions

### Revisions
- `Workflow` carries stable identity (`id`, `title`, `workflow_engine`). All mutable content (`definition`, `workflow_parameters`, `labels`) lives on `WorkflowRevision`.
- Any PATCH to a versioned field appends a new revision and bumps `increment`. A title-only PATCH updates the workflow row in place.
- `WorkflowRun` pins to the `WorkflowRevision` it was submitted under, so in-flight runs are immune to subsequent PATCHes.
- Soft-deleted workflows free their title (partial unique index `WHERE removed = false`); re-POSTing the same title mints a fresh workflow.

### POST conflicts
`POST /v1/workflows` returns **409** when the title already exists with `detail.existing_workflow.id` in the body. Clients decide whether to PATCH the existing workflow or treat it as a no-op.

### Mutation gating (`DEV_MODE`)
`PATCH /v1/workflows/{id}` and `POST /v1/workflows/{id}/revisions/{n}/restore` return **403** when the `DEV_MODE` env var is unset / false. POST (create) and DELETE (soft-delete) are always allowed.

### Labels
Workflows, runs, and tasks can be labeled arbitrarily. Labels enable flexible grouping and filtering:
- Adapters may only schedule runs with a certain label.
- Experiments can be grouped by a label (e.g., `kaapana.experiment`).

Any label whose key starts with `kaapana.immutable.` is treated as **immutable**: it cannot be removed or have its value changed across revisions. PATCHing an immutable label returns **422**. New immutable labels may be added at any time.

### Audit Trail
- API logs all key actions (creation, retrieval, updates) with workflow/run IDs.  
- Logs can be exported for auditing.  
- Future: a dedicated `audit_log` table may be introduced if compliance requires database-backed trails.  

### Error Handling & Edge Cases
- **Engine failure after workflow insert**: workflow exists in DB but no tasks are created. 
- **Network partition during run scheduling**: run may remain `PENDING` in DB. Sync will eventually correct state.
- **Retries**: completed runs cannot be re-triggered at the engine, but can be retried via API (status reset to `PENDING`).

---

## Roadmap & future TODOs
* Integrate user & permission model for audit requirement integration.
* Event sourcing / message bus for scaling cross-system communication.
* A dedicated `audit_log` table, if compliance requires it.

## Development
* Ensure `local-only/base-python-cpu:latest` exists via `docker image ls | grep local-only/base-python-cpu`
* Run `DOCKER_BUILDKIT=0 docker compose build`
* Run `docker compose up` 
* Ensure all tests pass via `cd files/tests && pytest workflow_run_test.py workflow_test.py`
* Follow existing formatting using `black` for your changes
* Provide end to end tests for new use cases introduced


## Glossary
- **Workflow**: A set of tasks and their dependencies.  
- **WorkflowEngine**: External system that schedules and executes workflows.  
- **WorkflowDefinition**: Engine-interpretable specification (e.g., DAG file).  
- **WorkflowRun**: A single execution of a workflow.  
- **WorkflowExecution**: The engine’s execution entity (e.g., DAGRun in Airflow).  
- **Task**: A step in the workflow definition.  
- **TaskRun**: A single execution of a task within a workflow run.  
