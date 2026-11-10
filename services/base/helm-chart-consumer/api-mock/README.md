# Helm Chart Consumer API mock

A proposal for the API of the Helm Chart Consumer, described in [../concept.md](../concept.md). Every route has a
typed signature, a docstring that says what it does, and pydantic models for its input and output. Every route
returns fixed example data and changes nothing. The examples reuse some of the applications and their deployed
instances from the seed data of the UI mock in [../docker](../docker).

## Run it

```bash
cd services/base/helm-chart-consumer/api-mock
docker compose up --build
```

Open http://localhost:5055/docs. Stop it with `docker compose down`.

Without Docker, run `pip install -r requirements.txt` in a virtual environment, then
`uvicorn app.main:app --port 5055`.

## Layout

| File | Content |
|---|---|
| `app/models.py` | Request and response models, including `HelmChartContent`, the model of `helm-chart-content.json` |
| `app/routers/applications.py` | Applications and their versions. The Extension Manager registers and deregisters versions here. |
| `app/routers/releases.py` | Deploy, update, undeploy and status of deployed applications |
| `app/routers/projects.py` | Which applications are enabled in which project |
| `app/examples.py` | The example data the routes return |

See [../handoff.md](../handoff.md) for the reasons behind the API, the facts about the Extension Manager and the
gateway that the API depends on, and what an implementation has to take care of.
