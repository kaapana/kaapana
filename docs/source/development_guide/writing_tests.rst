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

A processing-container declares its contract in the
:file:`processing-container.json` inside the image. A :file:`task.json`
instantiates one of its task templates. The Task API CLI validates both files
and runs the task on Docker, with nothing else installed:

.. code-block:: bash

    python3 -m task_api.cli validate processing-container.json --schema pc
    python3 -m task_api.cli validate task.json --schema task
    python3 -m task_api.cli run task.json --mode docker

A run writes a :file:`task_run-<id>.pkl` to the working directory;
:code:`task_api.cli logs` reads that file. The run confirms that the container
finds its inputs at the paths its task template declares and writes its results
in the layout of :ref:`data_structure_convention`.

:ref:`processing_container_dev_guide` covers installing the CLI and describes
the :file:`task.json` format, including a minimal file to start from.

Local operators
===============

An operator deriving from ``KaapanaPythonBaseOperator`` or
``KaapanaBranchPythonBaseOperator`` runs its code in the Airflow process itself,
so a pytest test imports it and calls it directly, with no scheduler and no
platform. One deriving from ``KaapanaBaseOperator`` launches a pod and keeps its
logic in the container image. That logic is tested as a processing-container,
above. The suite lives in :file:`tests/operators`.

Ordinary imports do not work at the top of the file. The plugin directory has
to be on the path first, and an operator that pulls in modules from the
Airflow image needs those mocked as well. Take both from
:file:`tests/operators/utils.py` rather than spelling them out per file, so a
moved directory or a new module to mock is a one-line change for the whole
suite. In outline:

.. code-block:: python

    import sys

    from .utils import PLUGIN_DIR, mock_modules

    sys.path.insert(0, str(PLUGIN_DIR))
    mock_modules()  # only if the operator imports from the Airflow image

    # only now, not at the top of the file
    from kaapana.operators.<Module> import <name>

A test takes one of two shapes:

- calling a helper function over a table of cases with
  :code:`@pytest.mark.parametrize`, as in :file:`test_HelperThumbnails.py`
- building the operator in a pytest fixture and calling its :code:`start()`
  method, as in :file:`test_LocalDcm2JsonOperator.py`

DICOM inputs are not committed: :file:`generator.py` writes them per case to
the path it is given, with a parameter dictionary overriding individual tags.

Run the suite from the repository root, which is where the operators write
their scratch directory:

.. code-block:: bash

    pip install -r tests/requirements.txt
    pytest tests/operators

User interfaces
===============

The shell and most of its views carry a Playwright end-to-end suite of their
own, each with its own fixture that intercepts the app's backend calls in the
browser and serves fixture data. A suite therefore needs no cluster and no
backend.

Every view imports :code:`@kaapana/base-ui` and needs its :file:`dist/` built
first, see :ref:`ui_dev_loop`. There is no repository-wide setup: each app
installs into its own :file:`docker/files`, so run the steps below once per app,
and again whenever the app's lockfile changes:

.. code-block:: bash

    cd services/base/<app>-ui/docker/files
    npm ci
    npx playwright install chromium   # once per pinned playwright version

From then on the suite runs on its own, because Playwright starts the app's
dev server:

.. code-block:: bash

    npx playwright test

Each app listens on its own fixed port, so the suites can run in parallel. The
shell additionally ships vitest unit suites, run with
:code:`npm run test:unit`, for logic that a browser test reaches only
indirectly, such as the API client and the stores.

A new view brings its own suite and fixture with it, and has to be entered in
the CI matrix by hand, or it is never tested. The port registry, the
mock-backend fixture and that matrix are described in the
:ref:`UI development guide <ui_testing>`.

Where to go next
================

- :file:`tests/README.md` in the repository: where a suite belongs, which test
  level to pick, and how to get it running in the pipeline.
- :file:`ci/README.md` together with :file:`ci/pipeline/unit-tests.yml`: how
  the suites run in CI. The pipeline reports test results and coverage back
  into the merge request.
