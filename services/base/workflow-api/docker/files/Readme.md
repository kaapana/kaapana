# Readme 

## Motivation
One key feature of Kaapana is the executing of *Workflows*.
A workflow consists of multiple steps that may depend on each other.
Commonly, these steps correspond to *tasks* like data-retrieval, pre-processing, processing, post-processing and result-persisting.
There exist several *Workflow Engines*, e.g. AirFlow, KubeFlow, ArgoCD, that are helpful for designing Workflows, scheduling *Workflow Runs* and monitoring their state.
Kaapana aims to be **agnostic** to the specific Workflow Engine that is most convenient for you to develop Workflows.
Hence, in Kaapana a Workflow simply corresponds to a *Workflow Definition* that is interpretable by the Workflow Engine of your choice,
e.g. for Airflow a dag-file corresponds to the Workflow Definition

Furthermore, Kaapana wants to provide a **unified interface** that supports an exclusive list of commonly required actions when managing Workflows and their execution:
* **Post Workflows**
* **Configuring Workflow Execution**
* **Receiving lifecycle information on Workflow Runs and Task Run**
* **Manually post lifecycle events to TaskRuns and WorkflowRuns, e.g. *CANCELED*, *RETRY***
* **Receiving logs of Task Runs**

This interface will be provided in the form of a **stable Rest API**.

Having this interface in Kaapana will help to have a clear **separation of concerns** in its API landscape.
The exclusive feature list will help to keep the code base **clean and free of convoluting features**.

### Admin API
Additionally to the Workflow API we will provide admin Rest endpoints for housekeeping e.g.:
* Delete archived objects
* Update objects


## Architecture
### Workflow Engine Adapter
The Workflow API is by concept independent of any Workflow Engine.
Therefore, a component is required that handles communication between the Workflow API and any Workflow Engine.
We will call this component *Workflow Engine Adapter*.

* Receive Workflow Definitions and create them in a Workflow Engine.
* Validate that Workflow Definitions are valid.
* Fetch WorkflowRuns from the Workflow API and:
    * If state is up-for-scheduling -> Schedule in Workflow Engine
    * If state is Running -> Update state depending on corresponding state of the Worklfow Execution in Workflow Engine
    * If state is CANCELED -> Cancel Workflow Execution in Workflow Engine
    * If state is RETRY -> Retry Workflow Execution in Workflow Engine
* ...


## Design decisions

### Database Relations
* **Workflow**
    * `Workflow 1 — n WorkflowRun` (a workflow can have many runs).
    * `Workflow 1 — n Task` (a workflow has many tasks).
    * `Workflow m — n Label` (workflows can have multiple labels via workflow_label).

* **WorkflowRun**
    * `WorkflowRun n — 1 Workflow` (each run belongs to a specific workflow).
    * `WorkflowRun m — n Label` (runs can have labels via workflowrun_label).
    * `WorkflowRun 1 — n TaskRun` (each run has multiple task runs).

* **Task**
    * `Task n — 1 Workflow` (belongs to a workflow).
    * `Task 1 — n TaskRun` (each task can spawn multiple runs).
    * `Task m — n Task` (via DownstreamTask) (dependency graph between tasks).
    * `DownstreamTask` Association table between Task.task_id and Task.downstream_task_id. Enforces unique pair.

* **TaskRun**
    * `TaskRun n — 1 Task` (links to task definition).
    * `TaskRun n — 1 WorkflowRun` (links to workflow execution instance).

* **Label**
    * `Label m — n Workflow`
    * `Label m — n WorkflowRun`

### Labels
One key design decision is to allow very generic labeling of objects in the Workflow API.
The main purpose for labels is, that clients can easily add information to objects that determine how they should be handled my other clients.
In this context note, that the Workflow API is not responsible that a Workflow Run is scheduled on a Workflow Engine.

**Examples:**
* A *Workflow Engine Adapter* can fetch only those Workflow Runs with a specific label and schedule them on the corresponding Workflow Enigne
* A collection of Workflow Runs could be tight together by a unique value of an `kaapana.experiment` label

### Connecting Workflow API to Workflow Engine
#### Implementation with Celery:
Creates two tasks in Celery whenever a WorkflowRun is created:
* One for triggering the DAG
* Upon success: Two tasks one for monitoring the state of the DagRun and its TaskRuns.

```mermaid
sequenceDiagram

    participant Client as Client
    participant API as Workflow API
    participant DB as DB
    participant Celery as Celery Worker
    participant Airflow as Airflow

    Client->>API: POST /workflow-runs
    API->>DB: Create WorkflowRun (state=PENDING)
    API->>Celery: Enqueue Trigger Task
    Celery->>Airflow: Trigger DAGRun
    Airflow-->>Celery: DAGRun created
    Celery->>DB: Update WorkflowRun (state=RUNNING)
    Celery->>Celery: Enqueue Monitoring Task
    loop Poll DAGRun state
        Celery->>Airflow: Get DAGRun status
        Airflow-->>Celery: Status update
        Celery->>DB: Update WorkflowRun state
    end
```

Drawbacks:
* Celery workers blocked with two task per WorkflowRun until the DagRun ends in a final state.
* Overhead of Celery deployment and Redis database

#### Comparison of different approaches for connecting the Workflow API to Workflow Engines
| Approach            | Example Frameworks            | Core Idea                                      | Pros                                                      | Cons                                                           | Best For |
|---------------------|-------------------------------|------------------------------------------------|-----------------------------------------------------------|----------------------------------------------------------------|----------|
| **Task Queue**      | Celery, RQ, Dramatiq, Huey    | Push jobs into a queue, workers consume them   | Mature ecosystem, retries, distributed, Python-native     | Can get noisy with many per-run tasks, state drift, coupling   | General background jobs, async triggers |
| **Scheduler**       | APScheduler, K8s CronJobs     | Run periodic reconciliation loops              | Simple, low overhead, easy to reason about                | Not event-driven, can add latency, single point unless scaled  | Periodic sync tasks, controller-style loops |
| **Event Bus**       | Kafka, RabbitMQ, SQS, PubSub  | Emit events (`WorkflowRunCreated`), consumers react | Decoupled, resilient, scalable, multiple consumers possible | Extra infra complexity, less Python-native, requires ops team | Large-scale, multi-service event-driven systems |
| **Workflow Engine** | Temporal, Argo Workflows      | Engine manages state transitions + retries     | Strong guarantees, history, retries, observability        | Heavyweight, steep learning curve, locks you into model        | Complex workflows, compliance/audit requirements |

#### Hybrid approach

1. Triggering a Workflow with FastAPI background task
```mermaid
sequenceDiagram
    participant Client as Client
    participant API as Workflow API (FastAPI)
    participant DB as Workflow API DB
    participant BG as FastAPI Background Task
    participant Adapter as Workflow Engine Adapter
    participant Engine as Workflow Engine

    Client->>API: POST /workflow-runs
    API->>DB: Create WorkflowRun (state=PENDING)
    API->>BG: Start background job (schedule Workflow)
    API-->>Client: 201 Created (returns WorkflowRun)

    BG->>Adapter: trigger_workflow_run(workflow, run_id)
    Adapter->>Engine: Create WorkflowRun (DAGRun/etc.)
    Engine-->>Adapter: Ack (Workflow scheduled)
    Adapter->>DB: Update WorkflowRun (state=RUNNING)
```

2. Getting WorkflowRun information from WorkflowEngine

```mermaid
sequenceDiagram
    participant Client as Client
    participant API as Workflow API
    participant DB as Workflow API DB
    participant Adapter as Workflow Engine Adapter
    participant Engine as Workflow Engine

    Client->>API: GET /workflow-runs/{id}
    API->>DB: Read WorkflowRun
    alt State is final (COMPLETED/FAILED/CANCELLED)
        API-->>Client: Return state from DB
    else State is active (PENDING/RUNNING/RETRYING)
        API->>Adapter: get_workflow_run(run_id)
        Adapter->>Engine: Fetch current state
        Engine-->>Adapter: Current state
        Adapter->>DB: Update WorkflowRun state
        API-->>Client: Return updated state
    end
```


3. Periodic sync of Workflow API DB with Workflow Engine
```mermaid
sequenceDiagram
    participant Cron as K8s CronJob
    participant Adapter as Workflow Engine Adapter
    participant Engine as Workflow Engine
    participant DB as Workflow API DB

    loop Periodic Sync (e.g., every 30s)
        Cron->>Adapter: list_workflow_runs(filter=active, pagination)
        Adapter->>Engine: Query runs with filters
        Engine-->>Adapter: Return page of WorkflowRuns + states
        Adapter->>DB: Upsert WorkflowRun states
        note over Adapter,DB: Continue with pagination until complete
    end
```

## Glossary

* Workflow:
* WorkflowEngine:
* WorkflowDefinition:
* WorkflowRun:
* WorkflowExecution: 
* Task:
* TaskRun: