# Tests

What lives here, and how to run it. Writing a suite of your own is covered in
[../ci/README.md](../ci/README.md), section 9.

Two suites live here. Every other suite lives next to the code it covers, most
under `services/**/docker/**/tests/` or `lib/<package>/tests/`, and the system
tests that build, deploy and exercise a platform under
`ci/ci-code/integration_tests/`.

| Path | Covers | CI job |
|---|---|---|
| `operators/` | Airflow operators from `data-processing/kaapana-plugin`, called directly, without a scheduler or a platform | `unit_tests` |
| `ui/` | Playwright against a running instance, needs its URL and the default credentials, see [ui/README.md](ui/README.md) | `playwright_ui_tests` (stage `test`) |

## Running a suite

From the repository root:

```bash
pip install -r tests/requirements.txt
pytest tests/operators
```

A service suite runs the same way, by its path and with the `requirements.txt`
that belongs to it. A library suite under `lib/` has none. Its dependencies sit
in the package's `pyproject.toml` and the extras differ per package, so take the
install line from the suite's job in
[../ci/pipeline/unit-tests.yml](../ci/pipeline/unit-tests.yml).

Stay in the repository root, as CI does. `pytest.ini` limits discovery to
`tests/`, so a bare `pytest` finds the operator tests and nothing else. The
operator tests also write their scratch DICOM relative to the working
directory.

The whole `tests` stage runs locally through gitlab-ci-local, see "Running the
pipeline locally" in [../ci/README.md](../ci/README.md).

## Where to go next

- [../ci/README.md](../ci/README.md), section 9: where a suite belongs, what
  its `conftest.py` has to carry, which test level to pick, and how to get it
  running in the pipeline. Section 11 covers what the pipeline reports back.
- [Writing Tests](../docs/source/development_guide/writing_tests.rst) in the
  development guide: testing a processing-container, a local operator or a
  user interface on a development machine.
