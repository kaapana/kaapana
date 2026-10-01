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

VS Code
--------

Install the `Ruff extension <https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff>`_
(:code:`charliermarsh.ruff`), then in your :code:`.vscode/settings.json`:

.. code-block:: json

    {
      "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
          "source.organizeImports.ruff": "explicit"
        }
      }
    }

The extension reads :code:`ruff.toml` from the repository root, so the editor
formats exactly the way the pre-commit hook and the :code:`lint: [ruff]` job do.

Usage
------
Format and lint the whole repository from its root:

.. code-block:: bash

    ruff format .          # rewrite files
    ruff check --fix .     # sort imports, drop unused ones, report the rest

    ci/ci-code/lint/ruff_lint.sh   # exactly what lint: [ruff] runs: report, change nothing

Both are safe to run repeatedly. Pass a path to limit them to one file or
directory.

Pre-commit hooks
-----------------

.. important::
  Install the hooks before committing — CI runs the same checks and fails the
  pipeline on any finding:

  .. code-block:: bash

      pip install pre-commit && pre-commit install

The hooks live in :code:`.pre-commit-config.yaml`. On commit they run one
after the other:

1. **ruff** pins the same Ruff version the CI job uses. On commit it formats
   the staged files and applies the safe lint fixes. When it changes
   something, review the result and commit again.

2. **helm-lint** runs :code:`kaapana-build --lint-only` when the commit
   changes a chart. It lints and validates the platform chart tree, exactly
   what the :code:`helm_lint` CI job does. It needs :code:`helm` and its
   kubeval plugin, the same as a local build; :code:`build_cli` is installed
   into the hook's own environment the first time it runs.

The commits that migrated the codebase to Ruff are listed in
:code:`.git-blame-ignore-revs`, so :code:`git blame` skips them. To make your
local git use that list:

.. code-block:: bash

    git config blame.ignoreRevsFile .git-blame-ignore-revs

Code quality report
--------------------
The :code:`lint: [ruff]` job also runs a wider ruleset,
:code:`ci/ci-code/lint/ruff-quality.toml`, that never fails a pipeline, and reports it in
the merge request Code Quality widget. The same run locally:

.. code-block:: bash

    ruff check --config ci/ci-code/lint/ruff-quality.toml --statistics .   # counts per rule
    ruff check --config ci/ci-code/lint/ruff-quality.toml .                # the findings
    ruff check --config ci/ci-code/lint/ruff-quality.toml --select UP006 --fix .   # one rule

Rules
------
:code:`ruff check` enforces pycodestyle errors, pyflakes (unused imports and
variables, undefined names) and import order.

CI
---
The :code:`lint` job in :code:`ci/pipeline/lint.yml` is a matrix with one
entry per linter, shown as one :code:`lint` group in the pipeline. Every entry
runs :code:`ci/ci-code/lint/<linter>_lint.sh`, which installs its own tool and
runs the same checks locally and in CI. Each entry publishes its advisory
findings to the merge request Code Quality widget and fails the pipeline on
formatting drift or an enforced rule. :code:`ruff_lint.sh` checks that its
:code:`RUFF_VERSION` matches the :code:`rev` of the ruff hook in
:code:`.pre-commit-config.yaml`, so the versions cannot drift. Helm charts are
checked by the separate :code:`helm_lint` job.

To add a linter, add its name to the :code:`LINTER` matrix and a matching
:code:`ci/ci-code/lint/<linter>_lint.sh`; if the tool can produce a Code Quality
report, write it to :code:`gl-code-quality-report.json`.
