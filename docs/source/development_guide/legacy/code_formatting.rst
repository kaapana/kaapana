.. _code_formatting:

Code Formatting
**********************************
Ruff
---------------------

All Python code in Kaapana is formatted and linted with `Ruff <https://docs.astral.sh/ruff/>`_,
which replaced Black, isort and flake8. One file at the repository root,
:code:`ruff.toml`, holds the whole configuration: 120 character lines,
Black-compatible formatting, isort-compatible import sorting.

Installation
--------------

.. code-block:: bash

    pip install ruff

Usage
------
Format and lint the whole repository from its root:

.. code-block:: bash

    ruff format .          # rewrite files
    ruff check --fix .     # sort imports, drop unused ones, report the rest

Both are safe to run repeatedly. Pass a path to limit them to one file or
directory.

Pre-commit hook
-----------------

.. important::
  Install the hook before committing — CI runs the same two commands and the
  ``lint`` job fails the pipeline on any difference:

  .. code-block:: bash

      pip install pre-commit && pre-commit install

The hook lives in :code:`.pre-commit-config.yaml` and pins the same Ruff
version the CI job uses. On commit it formats the staged files and applies the
safe lint fixes. When it changes something, review the result and commit
again.

The commit that migrated the codebase to Ruff is listed in
:code:`.git-blame-ignore-revs`, so :code:`git blame` skips it. To make your
local git use that list:

.. code-block:: bash

    git config blame.ignoreRevsFile .git-blame-ignore-revs

Code quality report
--------------------
The pipeline's :code:`code_quality` job runs a wider ruleset that never fails a
pipeline, and reports it in the merge request Code Quality widget. The same run
locally:

.. code-block:: bash

    ruff check --config ci/ruff-quality.toml --statistics .   # counts per rule
    ruff check --config ci/ruff-quality.toml .                # the findings
    ruff check --config ci/ruff-quality.toml --select UP006 --fix .   # one rule

Rules
------
:code:`ruff check` enforces pycodestyle errors, pyflakes (unused imports and
variables, undefined names) and import order. The pipeline's :code:`code_quality` job reports them in the merge request Code Quality widget.
