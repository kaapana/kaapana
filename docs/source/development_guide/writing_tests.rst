.. _writing_tests:

=============
Writing Tests
=============

Three layers of an extension can be tested on a development machine, without a
deployed platform:

- a :term:`processing-container`, through the Task API CLI on Docker
- a local operator, through pytest
- a user interface, through a mock-backed browser suite

Anything that requires a running platform is covered by the integration tests
in the pipeline instead.

Processing containers
=====================

The Task API ships a CLI that runs a single task of a container on Docker,
without Airflow and without a deployed platform. To exercise a container
against your own data:

1. Put the test data in a local directory.
2. Write a :file:`task.json` whose input channel points at that directory.
3. Run it:

   .. code-block:: bash

       python3 -m task_api.cli run task.json --mode docker

``run`` parses the :file:`task.json` first, so a malformed one fails before any
container starts. The second file, the :file:`processing-container.json` that
declares what the image can do, is checked on its own:

.. code-block:: bash

    python3 -m task_api.cli validate processing-container.json --schema pc

:ref:`processing_container_dev_guide` covers installing the CLI, the fields of
a :file:`task.json` and a minimal file to start from.

Local operators
===============

Operators deriving from ``KaapanaPythonBaseOperator`` or
``KaapanaBranchPythonBaseOperator`` run their code in the Airflow process, so
pytest can import them and call them directly. Operators deriving from
``KaapanaBaseOperator`` only launch a container and keep their logic inside the
image; that logic is tested as a processing-container, above. The base class
decides this, not the name: most in-process operators are called ``Local*``,
but the prefix alone does not settle it, so check what the class derives from.

The suite lives in :file:`tests/operators`, and a test there is built like this.

**1. Put the plugin directory on the path and mock the Airflow image.** Both
come from
`utils.py <https://github.com/kaapana/kaapana/blob/develop/tests/operators/utils.py>`_:
``PLUGIN_DIR`` is the directory Airflow loads the operators from, and
``mock_modules`` stubs the modules that ship in the Airflow image alone, the
Kubernetes client, the MinIO and notification helpers and ``kaapanapy`` among
them:

.. code-block:: python

    import sys

    from .utils import PLUGIN_DIR, mock_modules

    sys.path.insert(0, str(PLUGIN_DIR))
    mock_modules()  # drop it if the import below works without it

**2. Import the operator, and only after those two lines:**

.. code-block:: python

    from kaapana.operators.LocalDcm2JsonOperator import LocalDcm2JsonOperator

**3. Generate the inputs.** DICOM files are not committed to the repository,
they are written per test case by
`generator.py <https://github.com/kaapana/kaapana/blob/develop/tests/operators/generator.py>`_.
Its :code:`generate_ct`, :code:`generate_seg` and :code:`generate_rtstruct` each
take a target path and a dictionary of DICOM tag names, which overrides
individual tags of the default series they build.

**4. Build the operator in a fixture and call it.** The fixture constructs the
operator, points its :code:`airflow_workflow_dir` at a scratch directory, writes
the generated files into the batch below it and calls :code:`start()`, as in
`test_LocalDcm2JsonOperator.py <https://github.com/kaapana/kaapana/blob/develop/tests/operators/test_LocalDcm2JsonOperator.py>`_.
Where the behaviour under test is a helper function rather than a whole
operator, there is neither fixture nor operator:
`test_HelperThumbnails.py <https://github.com/kaapana/kaapana/blob/develop/tests/operators/test_HelperThumbnails.py>`_
calls the function over a table of cases, one case per
:code:`@pytest.mark.parametrize` entry.

**5. Run the suite from the repository root**, which is where the operators
write their scratch directory:

.. code-block:: bash

    pip install -r tests/requirements.txt
    pytest tests/operators

User interfaces
===============

The shell ui and most of its views ship a Playwright end-to-end suite that
intercepts the backend calls in the browser and serves fixture data, so a suite
needs neither cluster nor backend. To run one:

1. Build :code:`@kaapana/base-ui` first if the app consumes it, see
   :ref:`ui_dev_loop` in the UI development guide.
2. Install the app's dependencies and the browser. There is no repository-wide
   setup, each app installs into its own :file:`docker/files`, so this is once
   per app and again whenever its lockfile changes:

   .. code-block:: bash

       cd services/base/<app>-ui/docker/files
       npm ci
       npx playwright install chromium

3. Run the suite. Playwright starts the app's dev server itself, and each app
   listens on its own fixed port, so suites can run in parallel:

   .. code-block:: bash

       npx playwright test

The shell ui additionally carries vitest unit suites for logic that a browser
test reaches only indirectly, such as the API client and the stores. Run them
with :code:`npm run test:unit`.

A new view brings its own suite and fixture with it, and has to be added to the
CI matrix by hand. A suite that is not in the matrix never runs in the pipeline.
The :ref:`UI development guide <ui_testing>` covers the port registry, the
mock-backend fixture and that matrix.

The Playwright suite in :file:`tests/ui` is a different thing. It drives a
deployed instance through a real login, so it takes a URL and credentials
instead of fixtures.

Where to go next
================

- `ci/README.md <https://github.com/kaapana/kaapana/blob/develop/ci/README.md>`_,
  section 9: where a suite for a service belongs, what its :file:`conftest.py`
  has to carry, which test level to pick, and how to give it a CI job.
- `tests/README.md <https://github.com/kaapana/kaapana/blob/develop/tests/README.md>`_:
  what the two suites in that directory cover and how to run them.
