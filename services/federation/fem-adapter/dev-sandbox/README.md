# fem-adapter dev-sandbox

A fully local, offline stand-in for the EUCAIM FEM-orchestrator + broker,
used to prove the fem-adapter <-> workflow-api integration end-to-end
against the **real** FEM-client software and the real pipe-delimited,
chunked RabbitMQ wire protocol -- no EUCAIM credentials or network access
required.

See `../README.md` for how this differs from the production
`eucaim-fem-chart` (mainly: plain-AMQP RabbitMQ with throwaway
guest/guest credentials instead of a real AMQPS broker+TLS, and building
FEM-client directly from a local clone rather than
`../fem-client-image`'s pinned-commit git clone).

## What's running

| service      | image/build                              | role |
|--------------|-------------------------------------------|------|
| `rabbitmq`   | `rabbitmq:3-management`                   | stand-in for the FEM-orchestrator's broker |
| `postgres`   | `postgres:17.7-alpine`                    | workflow-api's database |
| `workflow-api` | built from `../../../base/workflow-api/docker` | Kaapana workflow-api, `ENABLE_TEST_ADAPTER=true` (fakes a workflow engine via `DummyAdapter`, no real Airflow needed) |
| `fem-adapter`  | built from `../docker`                  | the bridge this task built |
| `fem-client`   | built from the real fem-client source (see below) | the real EUCAIM Federated Data Node client |

## Running it

1. Point `FEM_CLIENT_SRC_DIR` at a local clone of
   `https://gitlab.bsc.es/fl/fem-client.git` (defaults to the path this was
   developed against; override if yours is elsewhere):

   ```bash
   export FEM_CLIENT_SRC_DIR=/path/to/your/fem-client-clone
   ```

2. Build and start everything:

   ```bash
   docker compose up -d --build
   ```

3. Install `pika` on the host (only needed to run the mock orchestrator
   script itself, not part of the stack):

   ```bash
   pip install pika
   ```

4. Run the mock orchestrator. It publishes one `submit_run` command to
   FEM-client's queue exactly as the real FEM-orchestrator would, then
   consumes and reassembles FEM-client's chunked response:

   ```bash
   python3 mock_orchestrator.py
   ```

## What success looks like

`mock_orchestrator.py` prints the `chunk_start`/`chunk` messages it
received, confirms the sha256 checksum over the reassembled response, and
prints a final decoded JSON block that looks like:

```json
{
  "status": "Completed",
  "execution_id": "exec-xxxxxxxx",
  "workflow_run_id": 1,
  "external_id": "dummy-workflow-run-extid-1-123",
  "task_id": "kaapana-fem-smoketest"
}
```

`"status": "Completed"` confirms the full chain: FEM-client received and
parsed the `submit_run` command over RabbitMQ, ran `json_launcher.json`'s
`curl` against fem-adapter, fem-adapter created a Kaapana `Workflow` +
`WorkflowRun` in workflow-api and polled it to a terminal state, and
FEM-client shipped that JSON back over the chunked reply protocol.

To inspect the workflow-api state directly: `curl
http://localhost:8080/v1/workflow-runs/1`. RabbitMQ's management UI is at
`http://localhost:15672` (guest/guest).

## Cleaning up

```bash
docker compose down -v
```
