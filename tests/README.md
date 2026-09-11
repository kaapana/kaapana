# Tests

This directory holds the Airflow operator unit tests and the Playwright suite
that drives a deployed platform. Every other suite lives next to the code it
covers.

| Path | Covers | CI job |
|---|---|---|
| `operators/` | Airflow operators from `data-processing/kaapana-plugin`, called directly, without a scheduler or a platform | `unit_tests` |
| `ui/` | Playwright against a running instance, needs its URL and the default credentials, see [ui/README.md](ui/README.md) | `playwright_ui_tests` (stage `test`) |

Those usually sit under `services/**/docker/**/tests/` and
`lib/<package>/tests/`; the system tests that need a deployment live under
`ci/ci-code/integration_tests/`.

## Running them

From the repository root:

```bash
pip install -r tests/requirements.txt
pytest tests/operators
```

Any other suite runs the same way, by its path and with the `requirements.txt`
that belongs to it:

```bash
pip install -r <suite>/requirements.txt
pytest <suite>
```

Stay in the repository root, as CI does. `pytest.ini` limits discovery to
`tests/`, so a bare `pytest` finds the operator tests and nothing else, and
those tests write their scratch DICOM relative to the working directory.

The whole `tests` stage also runs on any machine with docker, see section 10 of
[../ci/README.md](../ci/README.md).

## Adding a suite

Put `tests/` next to the app package in the service's build context, usually
`docker/files/tests/` beside `docker/files/app/`, and name the files
`test_*.py`.

A `conftest.py` beside them carries up to three things:

```python
# Settings are read at import time, so set them before the app is imported.
# Dummy values are enough as long as nothing connects.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")

# Stub the modules that only ship in the base image, so the suite needs no image.
sys.modules.setdefault("kaapanapy", types.ModuleType("kaapanapy"))

# Make `import app` work whatever directory pytest was started from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

Every suite needs the last line, because the app code is not an installable
package. A suite that imports nothing heavy needs only that line, as in
[portal-api](../services/base/portal-api/docker/tests/conftest.py). One that
needs all three is
[notification-service](../services/base/notification-service/docker/files/tests/conftest.py).

Pin the suite's test dependencies with `==` in its own `requirements.txt`. The
job starts from the bare Python image named in `.test_template` and inherits
nothing. Runtime dependencies of the service belong in the service's
`requirements.txt`, not in the suite's.

## Choosing a test level

Three levels, from cheapest to most involved. Take the first one that reaches
the behaviour under test.

### Function

Logic reachable without a request: a [plain pytest](https://docs.pytest.org/)
test.

Setup appears only where the function takes a framework object as its input.
A fixture in `conftest.py` then builds the minimal version of that object, as
`make_request` does for an ASGI scope in the example.

Example:
[dicom-web-filter/test_scope.py](../services/data-separation/dicom-web-filter/docker/files/tests/test_scope.py)

### Synchronous route

A route whose database dependency can be faked. It runs in-process under a
`TestClient`, with that dependency replaced.

```python
client = TestClient(app)
app.dependency_overrides[get_async_db] = override_db
```

Example:
[notification-service/test_read_all.py](../services/base/notification-service/docker/files/tests/test_read_all.py)

### Async route with a database

A route that needs real database behaviour. SQLite in memory, one engine
shared by every connection, tables created per test, the app reached through
its ASGI interface. Without `StaticPool` every connection opens its own empty
database, and Postgres-only column types such as `JSONB` have to be mapped to
a portable one before the models are imported.

```python
engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)

async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
    ...
```

Example:
[workflow-api/tests/unit/conftest.py](../services/base/workflow-api/docker/files/tests/unit/conftest.py)

## Getting it into CI

The jobs live in [../ci/pipeline/unit-tests.yml](../ci/pipeline/unit-tests.yml),
run in the `tests` stage and are gated by `CI_EXEC_UNIT_TESTS`. Whether a new
test runs depends on how its job was written:

1. A file under `tests/` runs without touching CI, because `unit_tests` passes
   the directory to pytest. New dependencies go into `tests/requirements.txt`.
2. The same holds wherever an existing job passes a directory. Where a job
   names a single file instead, a new file beside it stays silent until the
   job is changed.
3. A suite at a new location needs its own job:

```yaml
<name>_tests:
  extends: .pytest_template
  script:
    - pip install -r $KAAPANA_DIR/<suite>/requirements.txt
    - pytest $KAAPANA_DIR/<suite> --junitxml=<name>_report.xml
        --cov=<the app directory this suite exercises>
        --cov-report=term --cov-report=xml:coverage.xml
  artifacts:
    reports:
      junit:
        - <name>_report.xml
```

Then work through the checklist in section 9 of
[../ci/README.md](../ci/README.md), which covers the wiring a job needs beyond
its own script, and try it locally with
`gitlab-ci-local <name>_tests --variable CI_PIPELINE_SOURCE=web`.

## What CI reports back

Extending `.pytest_template` rather than `.test_template` adds a suite to the
coverage badge and to the line markers in the merge request diff. The JUnit
report feeds the pipeline's Tests tab either way. What is excluded from
coverage is set once in [../.coveragerc](../.coveragerc). Section 11 of
[../ci/README.md](../ci/README.md) lists the reports GitLab renders.
