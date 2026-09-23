.. _code_formatting:

Code Formatting
**********************************

Kaapana checks every Python, TypeScript and Vue file and every Dockerfile
with two kinds of tools.
Every one of them follows the same pattern: one configuration at the
repository root, one pinned tool version, a pre-commit hook that fixes what it
can on commit, and a CI job that checks the whole repository with the same
tool and configuration.

Formatter and linter
---------------------

A **formatter** decides how code looks: indentation, line breaks, quotes,
semicolons, trailing commas. It rewrites the file and never changes what the
code does, so everything it reports is fixed automatically. There is nothing
to discuss in review: the formatter's output is the style.

A **linter** decides whether code is likely wrong or hard to maintain: an
unused variable or import, an undefined name, :code:`any` where a type belongs,
a Vue template that cannot work. Some findings are fixed automatically (for
example sorting imports or :code:`let` → :code:`const`); the rest must be
fixed by hand.

.. list-table::
   :header-rows: 1

   * -
     - Python
     - TypeScript / Vue
     - Dockerfile
   * - Formatter
     - :code:`ruff format`
     - Prettier
     - none
   * - Linter
     - :code:`ruff check`
     - ESLint
     - hadolint
   * - Configuration
     - :code:`ruff.toml`
     - :code:`.prettierrc.json`, :code:`eslint.config.mjs`
     - :code:`.hadolint.yaml`
   * - Code quality report
     - :code:`ci/ruff-quality.toml`
     - :code:`ci/eslint-quality.config.mjs`
     - :code:`.hadolint.yaml`
   * - Pre-commit hook
     - :code:`ruff-check`, :code:`ruff-format`
     - :code:`ui-lint`
     - :code:`hadolint`
   * - CI job
     - :code:`lint: [ruff]`
     - :code:`lint: [ui]`
     - :code:`lint: [hadolint]`

The linters leave formatting to the formatters: ESLint's formatting rules are
switched off, so ESLint and Prettier never disagree.

Every linter has two rulesets. The **enforced** ruleset holds the rules whose
findings are bugs; the pre-commit hook and CI fail on it. The **advisory**
ruleset adds the rules the codebase does not meet yet; CI reports its findings
in the merge request Code Quality widget and never fails on them. Formatting
is always enforced.

One-time setup
---------------
From the repository root:

.. code-block:: bash

    pip install ruff pre-commit
    npm ci                  # ESLint and Prettier, into the root node_modules
    pre-commit install      # run the hooks on every commit

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

The whole codebase
-------------------
Format and lint the whole repository from its root:

.. code-block:: bash

    ruff format .          # formatter: rewrite files
    ruff check --fix .     # linter: sort imports, drop unused ones, report the rest

    ruff format --check --diff .   # what CI runs: report, change nothing
    ruff check .

All are safe to run repeatedly. Pass a path to limit them to one file or
directory.

The commits that migrated the codebase to Ruff are listed in
:code:`.git-blame-ignore-revs`, so :code:`git blame` skips them. To make your
local git use that list:

.. code-block:: bash

    git config blame.ignoreRevsFile .git-blame-ignore-revs

Rules
------
:code:`ruff check` enforces pycodestyle errors, pyflakes (unused imports and
variables, undefined names) and import order.

Code quality report
--------------------
The :code:`lint: [ruff]` job also runs a wider ruleset,
:code:`ci/ruff-quality.toml`, that never fails a pipeline, and reports it in
the merge request Code Quality widget. The same run locally:

.. code-block:: bash

    ruff check --config ci/ruff-quality.toml --statistics .   # counts per rule
    ruff check --config ci/ruff-quality.toml .                # the findings
    ruff check --config ci/ruff-quality.toml --select UP006 --fix .   # one rule

ESLint / Prettier
---------------------

All TypeScript and Vue code in Kaapana is formatted with
`Prettier <https://prettier.io/>`_ and linted with
`ESLint <https://eslint.org/>`_. The repository root holds the whole
toolchain, the same way :code:`ruff.toml` does for Python:

- :code:`package.json` and :code:`package-lock.json` pin Prettier, ESLint and
  the ESLint plugins. They hold nothing else; no app depends on them.
- :code:`.prettierrc.json` is the one Prettier style: no semicolons, single
  quotes, 100 character lines.
- :code:`eslint.config.mjs` is the one ESLint configuration for every app.
- :code:`.prettierignore` and the ignores in :code:`eslint.config.mjs` keep
  build output and third-party code out.

The apps carry no lint configuration or lint dependencies of their own, so a
new app is covered as soon as its files are committed.

Installation
--------------
From the repository root, once and again after every change to
:code:`package-lock.json`:

.. code-block:: bash

    npm ci

This needs Node.js 20.19 or newer. The pre-commit hook and
:code:`ci/ci-code/lint/ui_lint.sh` run :code:`npm ci` themselves when
:code:`node_modules` is missing or older than the lockfile.

VS Code
--------

Install the `Prettier <https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode>`_
(:code:`esbenp.prettier-vscode`),
`ESLint <https://marketplace.visualstudio.com/items?itemName=dbaeumer.vscode-eslint>`_
(:code:`dbaeumer.vscode-eslint`) and
`Vue (Official) <https://marketplace.visualstudio.com/items?itemName=Vue.volar>`_
(:code:`Vue.volar`) extensions, then in your :code:`.vscode/settings.json`:

.. code-block:: json

    {
      "[typescript][vue]": {
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
          "source.fixAll.eslint": "explicit"
        }
      }
    }

On save, Prettier formats the file and ESLint applies its automatic fixes; the
remaining ESLint findings are underlined in the editor. Open the repository
root as the workspace folder and run :code:`npm ci` there first: both
extensions take their configuration and their tool version from the root, so
the editor formats and lints exactly the way the pre-commit hook and the
:code:`lint: [ui]` job do.

The whole codebase
-------------------
Format and lint the whole repository from its root:

.. code-block:: bash

    npm run format         # formatter: prettier --write on every .ts/.mts/.tsx/.vue file
    npm run lint           # linter: eslint --fix, fixes what it safely can, reports the rest

    npm run format:check   # report, change nothing
    npm run lint:check
    npm run lint:quality   # the advisory ruleset, never enforced
    ci/ci-code/lint/ui_lint.sh   # exactly what CI runs: both checks on the committed files

All are safe to run repeatedly. For one file or directory, call the tools
directly:

.. code-block:: bash

    npx prettier --write "services/base/portal-ui/**/*.{ts,mts,tsx,vue}"
    npx eslint --fix services/base/portal-ui

.. note::
  Do not run :code:`npx prettier --write .`: without a file pattern Prettier
  also rewrites every YAML, JSON and Markdown file in the repository.
  :code:`npm run format` limits it to TypeScript and Vue.

Rules
------
:code:`eslint.config.mjs` enforces the rules whose findings are bugs:

- :code:`eslint-plugin-vue` *essential*: errors that break a Vue component,
  such as an invalid :code:`v-for`, a mutated prop or a :code:`ref` used
  without :code:`.value`. :code:`valid-v-slot` allows Vuetify's
  :code:`#item.<key>` slot names. Unused components and template variables and
  single-word component names are left to the advisory ruleset.
- A few ESLint core rules: :code:`no-debugger`, :code:`no-dupe-else-if`,
  :code:`no-duplicate-case`, :code:`no-self-assign`,
  :code:`no-unsafe-finally`, :code:`use-isnan`, :code:`valid-typeof`.
- Formatting rules are off: Prettier owns formatting.

Code quality report
--------------------
The :code:`lint: [ui]` job also runs a wider ruleset,
:code:`ci/eslint-quality.config.mjs`, that never fails a pipeline, and
reports it in the merge request Code Quality widget. It adds:

- :code:`typescript-eslint` *recommended*: unused variables, :code:`any`,
  :code:`prefer-const` and similar. No rule needs type information, so ESLint
  never resolves an app's dependencies.
- :code:`@vitest/eslint-plugin` for :code:`src/**/__tests__` and
  :code:`eslint-plugin-playwright` for :code:`e2e/` and :code:`tests/ui`.

The same run locally:

.. code-block:: bash

    npm run lint:quality
    npx eslint --config ci/eslint-quality.config.mjs services/base/portal-ui

Each rule is documented on its own page, linked from the Code Quality widget.

Hadolint
---------------------

Every Dockerfile in Kaapana is linted with
`hadolint <https://github.com/hadolint/hadolint>`_. It checks Dockerfile best
practice (pinned package versions, :code:`WORKDIR` instead of :code:`cd`,
:code:`--no-install-recommends`, :code:`COPY` instead of :code:`ADD`) and runs
`ShellCheck <https://www.shellcheck.net/>`_ over the shell in every
:code:`RUN`. There is no established Dockerfile formatter, so there is no
formatting check. One file at the repository root, :code:`.hadolint.yaml`,
holds the whole configuration.

Installation
--------------
The pre-commit hook installs hadolint itself. For the editor and for running
it by hand:

.. code-block:: bash

    pip install hadolint-py     # or download the binary from the hadolint releases page

VS Code
--------

Install the `hadolint extension <https://marketplace.visualstudio.com/items?itemName=exiasr.hadolint>`_
(:code:`exiasr.hadolint`). It runs the :code:`hadolint` on your :code:`PATH`
and reads :code:`.hadolint.yaml` from the repository root, so findings are
underlined in the editor exactly as the pre-commit hook and the
:code:`lint: [hadolint]` job report them.

The whole codebase
-------------------
From the repository root:

.. code-block:: bash

    pre-commit run hadolint --all-files                # no installation needed
    git ls-files -z -- '*Dockerfile' | xargs -0 hadolint   # with hadolint on your PATH

Pass a path to check one Dockerfile: :code:`hadolint services/base/portal-ui/docker/Dockerfile`.

Rules
------
All of hadolint's rules apply, except three that Kaapana's build conventions
trigger on every image; :code:`.hadolint.yaml` ignores them:

- :code:`DL3007`: :code:`FROM local-only/<image>:latest` is an image
  :code:`kaapana-build` produces in the same build, not a floating upstream tag.
- :code:`DL3022`: :code:`COPY --from=constraints` (and :code:`lib`,
  :code:`charts`) are build contexts :code:`kaapana-build` passes in, not
  stages.
- :code:`DL3048`: :code:`LABEL IMAGE`, :code:`VERSION` and
  :code:`BUILD_IGNORE` are the uppercase keys :code:`kaapana-build` reads.

:code:`.hadolint.yaml` sets :code:`failure-threshold: error` and raises the
rules that catch a broken Dockerfile to *error*; only these fail the
pre-commit hook and :code:`lint: [hadolint]`:

- :code:`DL1000`: the Dockerfile cannot be parsed.
- :code:`DL3000`: :code:`WORKDIR` is not an absolute path.
- :code:`DL3011`: an :code:`EXPOSE` port is out of range.
- :code:`DL3012`, :code:`DL4003`, :code:`DL4004`: more than one
  :code:`HEALTHCHECK`, :code:`CMD` or :code:`ENTRYPOINT`; only the last one
  takes effect.
- :code:`DL3021`: :code:`COPY` with several sources to a destination not
  ending in :code:`/`.
- :code:`DL3023`: :code:`COPY --from` refers to its own stage.
- :code:`DL3024`: two stages share a name.
- :code:`DL3044`: an :code:`ENV` refers to itself.
- :code:`DL3061`: an instruction comes before :code:`FROM` or :code:`ARG`.

ShellCheck findings of level *error* (shell in a :code:`RUN` that cannot be
parsed) fail as well. Every other rule is advisory: hadolint's own *error*
rules that are not in this list (:code:`DL3004`, :code:`DL3020`,
:code:`DL3026`, :code:`DL3043`, :code:`DL4000`) are lowered to *warning*, and
all findings are published to the merge request Code Quality widget. To
silence one finding where it is intended, put :code:`# hadolint ignore=DL3008`
on the line above the instruction.

Pre-commit hooks
-----------------

.. important::
  Install the hooks before committing — CI runs the same checks and the
  :code:`lint` job fails on any difference:

  .. code-block:: bash

      pip install pre-commit && pre-commit install

The hooks live in :code:`.pre-commit-config.yaml` and run on the staged files
only:

- **ruff-check** and **ruff-format** lint and format Python files.
  pre-commit installs the pinned Ruff version into its own environment.
- **ui-lint** runs :code:`ci/ci-code/lint/ui_lint.sh` on staged TypeScript
  and Vue files: :code:`eslint --fix`, then :code:`prettier --write`. It
  needs :code:`node` and :code:`npm` on your :code:`PATH`; the script
  installs the root toolchain on first use.
- **hadolint** lints staged Dockerfiles. pre-commit installs the pinned
  hadolint version into its own environment.

When a hook changes a file, the commit stops: review the change, stage it and
commit again. When a hook reports a linter finding it cannot fix, fix it by
hand and commit again.

Run the hooks without committing:

.. code-block:: bash

    pre-commit run                     # on the staged files
    pre-commit run --all-files         # on the whole repository
    pre-commit run ui-lint --all-files # one hook only

CI
---
The :code:`lint` job in :code:`ci/pipeline/lint.yml` is a matrix with one
entry per linter, shown as one :code:`lint` group in the pipeline. Each entry
publishes its advisory findings to the merge request Code Quality widget;
GitLab merges the reports of all entries into one widget. Each entry fails
the pipeline on formatting drift or an enforced rule.

Until the TypeScript/Vue codebase is formatted and meets the enforced ruleset,
:code:`lint: [ui]` is allowed to fail and only warns.

.. list-table::
   :header-rows: 1

   * - Job
     - Checks
     - Code Quality report
     - Run it locally
   * - :code:`lint: [ruff]`
     - :code:`ruff format --check`, :code:`ruff check`
     - the wider :code:`ci/ruff-quality.toml` ruleset, advisory
     - :code:`ruff format --check --diff . && ruff check .`
   * - :code:`lint: [ui]`
     - :code:`prettier --check`, :code:`eslint`
     - the wider :code:`ci/eslint-quality.config.mjs` ruleset, advisory
     - :code:`ci/ci-code/lint/ui_lint.sh`
   * - :code:`lint: [hadolint]`
     - :code:`hadolint`, *error* level only
     - the hadolint findings, all levels, advisory
     - :code:`pre-commit run hadolint --all-files`

The versions cannot drift between your machine and CI: the job checks that its
:code:`RUFF_VERSION` and :code:`HADOLINT_VERSION` match the :code:`rev` of
their hooks in :code:`.pre-commit-config.yaml`, and ESLint and Prettier come from the root
:code:`package-lock.json` everywhere.

To add a linter, add its name to the :code:`LINTER` matrix and a matching
case to the job's script; if the tool can produce a Code Quality report,
write it to :code:`gl-code-quality-report.json`.
