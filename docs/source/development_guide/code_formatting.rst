.. _code_formatting:

Code Formatting
**********************************

Python, TypeScript/Vue, Markdown/JSON/YAML, Dockerfiles and Helm charts are
checked by a pre-commit hook on every commit and by CI jobs. Both use the
same configuration and the same pinned tool versions.

Every check belongs to one of three kinds:

- **Format**: layout only, fixed by the formatter, pre-commit hook does that automatically. The pre-commit hook and the
  :code:`format` CI job fail on it.
- **Validate** (blocking): syntax errors and the blocking rulesets. The
  pre-commit hook and the :code:`validate` CI job fail on them.
- **Lint** (advisory): the stricter rulesets. The :code:`lint` CI job
  publishes their findings in the merge request Code Quality widget and never
  fails. Pre-commit hook does not run them.

.. list-table::
   :header-rows: 1

   * - Tool
     - Format
     - Validate
     - Lint
   * - Ruff
     - :code:`ruff format`
     - :code:`ruff.toml`
     - :code:`ruff-quality.toml`
   * - Prettier
     - :code:`.prettierrc.json`
     -
     -
   * - ESLint
     -
     - :code:`eslint.config.mjs`
     - :code:`eslint-quality.config.mjs`
   * - hadolint
     -
     - :code:`.hadolint.yaml`
     - :code:`hadolint-quality.yaml`
   * - Helm
     -
     - helm lint, kubeconform
     - :code:`kube-linter-quality.yaml`

The advisory configs are in :code:`ci/ci-code/lint/`. Each tool has one
script there, :code:`ci/ci-code/lint/<linter>_lint.sh format|validate|lint`, which
installs the tool and runs exactly what the CI job runs.

Setup
-----

From the repository root:

.. code-block:: bash

    pip install ruff pre-commit
    npm ci                  # ESLint and Prettier, needs Node.js 20.19 or newer
    pre-commit install

.. code-block:: bash

    pre-commit run --all-files               # all hooks on the whole repository
    pre-commit run ui-lint --all-files       # one hook
    SKIP=hadolint,helm-lint git commit ...   # skip hooks for one commit

When a hook changes a file, the commit stops: review the change, stage it and
commit again.

Scope
-----

- **Pre-commit** checks the staged files only. Helm is the exception (see
  :ref:`code_formatting_helm`).
- **CI** checks the whole repository. The job log lists every finding. The
  Code Quality widget shows only the findings that are new or resolved
  compared with the target branch.
- A failing :code:`format: [ruff]`, :code:`validate: [ruff]` or
  :code:`validate: [hadolint]` job fails the pipeline.
  :code:`format: [prettier]`, :code:`validate: [ui]` and
  :code:`validate: [helm]` are allowed to fail until the existing findings
  are fixed, so they only warn. :code:`lint` jobs never fail.

Ruff
----

Python is formatted and linted with `Ruff <https://docs.astral.sh/ruff/>`_.
Configuration: :code:`ruff.toml` (blocking) and
:code:`ci/ci-code/lint/ruff-quality.toml` (advisory).
Rule reference: `Ruff rules <https://docs.astral.sh/ruff/rules/>`_.

.. code-block:: bash

    ruff format . && ruff check --fix .   # fix the whole repository
    ci/ci-code/lint/ruff_lint.sh format   # format: [ruff]
    ci/ci-code/lint/ruff_lint.sh validate # validate: [ruff]
    ci/ci-code/lint/ruff_lint.sh lint     # lint: [ruff], advisory

Scope
^^^^^

- Pre-commit: staged :code:`.py`, :code:`.pyi` and :code:`.ipynb` files.
- CI: the whole repository.
- Some vendored third-party files are excluded in :code:`ruff.toml`.

Blocking
^^^^^^^^

The pre-commit hook applies safe automatic fixes and fails. CI applies no fixes
and fails.

- **Formatter** (:code:`format`): code must match Ruff's Black-compatible
  style, with 120 character lines.
- :code:`E4`: import placement, such as several imports on one line.
- :code:`E7`: statement errors, such as a bare :code:`except:` or
  :code:`== None`.
- :code:`E9`: syntax errors and files that cannot be read.
- :code:`F` (pyflakes): unused imports and variables, undefined names.
- :code:`I` (isort): import order and grouping.

Advisory
^^^^^^^^

- :code:`E`, :code:`W` (pycodestyle): all style errors and warnings, such as
  whitespace and blank lines.
- :code:`B` (flake8-bugbear): likely bugs, such as mutable default arguments.
- :code:`C4` (flake8-comprehensions): unnecessary comprehensions and
  :code:`list()` or :code:`dict()` calls.
- :code:`SIM` (flake8-simplify): code that can be written more simply.
- :code:`UP` (pyupgrade): syntax that Python 3.12 can express more simply,
  such as :code:`X | None`.
- :code:`RUF`: Ruff's own rules, such as mutable class defaults.
- :code:`S` (flake8-bandit): security problems, such as :code:`shell=True`,
  requests without a timeout or :code:`verify=False`.
- :code:`BLE` (flake8-blind-except): :code:`except Exception:` that hides every
  error.
- :code:`ASYNC`: blocking calls, such as :code:`open()` or :code:`requests`,
  inside :code:`async` functions.
- :code:`DTZ` (flake8-datetimez): :code:`datetime` without a timezone.
- :code:`PERF` (Perflint): slow loop patterns.
- :code:`FAST`: FastAPI mistakes, such as dependencies without
  :code:`Annotated`.
- :code:`C90` (mccabe): functions that are too complex.
- :code:`ANN` (flake8-annotations): missing type annotations.
- :code:`T20` (flake8-print): :code:`print()` instead of logging.
- :code:`PTH` (flake8-use-pathlib): :code:`os.path` and :code:`open()` that
  :code:`pathlib` replaces.
- :code:`PL` (Pylint): too many arguments or branches, magic numbers and more.
- :code:`N` (pep8-naming): naming conventions.
- :code:`TRY`, :code:`G`, :code:`LOG`: exception handling and logging style,
  such as f-strings in logging calls.
- :code:`RET`, :code:`ARG`: return statement style, unused arguments.
- :code:`FBT` (flake8-boolean-trap): boolean positional arguments.
- :code:`ERA` (eradicate): commented-out code.

The advisory ruleset also reports :code:`E501` (lines the formatter cannot
shorten, such as long strings and comments) and :code:`B008` (including
FastAPI's :code:`Depends()` in default arguments). :code:`S101`
(:code:`assert`) is ignored in tests, where pytest relies on it.

Not selected
^^^^^^^^^^^^

- :code:`D` (pydocstyle): docstrings, left out for now.

ESLint
------

JavaScript, TypeScript and Vue are linted with `ESLint <https://eslint.org/>`_
and formatted with Prettier (see `Prettier`_).
Configuration: :code:`eslint.config.mjs` (blocking) and
:code:`ci/ci-code/lint/eslint-quality.config.mjs` (advisory).
Rule reference: `ESLint <https://eslint.org/docs/latest/rules/>`_,
`eslint-plugin-vue <https://eslint.vuejs.org/rules/>`_,
`typescript-eslint <https://typescript-eslint.io/rules/>`_,
`Vitest <https://github.com/vitest-dev/eslint-plugin-vitest#rules>`_,
`Playwright <https://github.com/playwright-community/eslint-plugin-playwright#rules>`_.

.. code-block:: bash

    npm run lint                       # fix the whole repository
    ci/ci-code/lint/ui_lint.sh validate # validate: [ui]
    ci/ci-code/lint/ui_lint.sh lint     # lint: [ui], advisory

Scope
^^^^^

- Pre-commit (hook :code:`ui-lint`): staged :code:`.js`, :code:`.mjs`,
  :code:`.cjs`, :code:`.jsx`, :code:`.ts`, :code:`.mts`, :code:`.tsx` and
  :code:`.vue` files.
- CI (:code:`validate: [ui]`, :code:`lint: [ui]`): all tracked files
  of these types.
- Excluded: minified :code:`*.min.js` files, build output, generated
  :code:`.d.ts` files, :code:`os-dashboards` and :code:`maintenance-page`.
- JavaScript files get the browser and Node.js globals.

Blocking
^^^^^^^^

The pre-commit hook applies the fixes it can and fails. CI fixes nothing.

- **eslint-plugin-vue** `essential <https://eslint.vuejs.org/rules/#priority-a-essential-error-prevention>`__:
  errors that break a Vue component, such
  as an invalid :code:`v-for`, a mutated prop, a :code:`ref` used without
  :code:`.value`, a single-word component name or an unused component.
- `vue/valid-v-slot <https://eslint.vuejs.org/rules/valid-v-slot.html>`__: :code:`v-slot` must be valid. Modifiers are
  allowed for Vuetify's :code:`#item.<key>` slots.
- `vue/block-lang <https://eslint.vuejs.org/rules/block-lang.html>`__: :code:`<script>` blocks must use
  :code:`lang="ts"`.

Advisory
^^^^^^^^

Every *recommended* preset of the installed plugins:

- **ESLint** *recommended*: likely bugs in plain JavaScript, such as useless
  :code:`catch` blocks or :code:`hasOwnProperty` called on the object.
- **eslint-plugin-vue** *recommended*: essential plus the
  `strongly recommended <https://eslint.vuejs.org/rules/#priority-b-strongly-recommended-improving-readability>`__
  and `recommended <https://eslint.vuejs.org/rules/#priority-c-recommended-potentially-dangerous-patterns>`__
  rules: component conventions, such as attribute order, prop defaults and
  :code:`v-html`.
- **typescript-eslint** *recommended*: such as :code:`any`, unused variables
  and :code:`prefer-const`. The type-checked variant is not used: it needs
  more than 4 GB of memory for the whole repository.
- **Vitest** *recommended*: test files in :code:`src/**/__tests__`.
- **Playwright** *recommended*: test files in :code:`e2e/` and
  :code:`tests/ui`.

Prettier
--------

JavaScript, TypeScript, Vue, Markdown, JSON and YAML files are formatted with
`Prettier <https://prettier.io/>`__.
Configuration: :code:`.prettierrc.json`, :code:`.prettierignore`.
Rule reference: `Prettier options <https://prettier.io/docs/options>`_.

.. code-block:: bash

    npm run format                          # fix the whole repository
    ci/ci-code/lint/prettier_lint.sh format # format: [prettier]

Scope
^^^^^

- Pre-commit (hook :code:`prettier`): staged files of these types. The hook is
  manual until the repository is formatted once:
  :code:`pre-commit run --hook-stage manual prettier`.
- CI (:code:`format: [prettier]`): all tracked files of these types.
- Excluded: Helm :code:`templates/` directories and the Helm-templated
  :code:`kaapana-realm.json`, which are Go templates, and
  :code:`package-lock.json` files. Helm templates have no formatter.

Blocking
^^^^^^^^

The pre-commit hook rewrites the files and fails. CI fixes nothing.

- **Markdown, JSON and YAML**: Prettier's default style.
- **JavaScript, TypeScript and Vue**: no semicolons, single quotes and 100
  character lines, the style the UI apps are written in.

Prettier never changes what a file means: it only changes indentation, quotes,
line breaks and spacing.

Hadolint
--------

Dockerfiles are linted with `hadolint <https://github.com/hadolint/hadolint>`_,
which also runs `ShellCheck <https://www.shellcheck.net/>`_ over every
:code:`RUN`. There is no formatter.
Configuration: :code:`.hadolint.yaml` (blocking) and
:code:`ci/ci-code/lint/hadolint-quality.yaml` (advisory).
Rule reference: `hadolint rules <https://github.com/hadolint/hadolint#rules>`_,
`ShellCheck checks <https://www.shellcheck.net/wiki/>`_.

.. code-block:: bash

    hadolint path/to/Dockerfile                                            # blocking
    hadolint -c ci/ci-code/lint/hadolint-quality.yaml path/to/Dockerfile # advisory
    ci/ci-code/lint/hadolint_lint.sh validate                            # validate: [hadolint]
    ci/ci-code/lint/hadolint_lint.sh lint                                # lint: [hadolint]

Scope
^^^^^

- Pre-commit: staged Dockerfiles.
- CI: all tracked :code:`*Dockerfile` files.

Blocking
^^^^^^^^

Only findings that stop the Dockerfile from building. hadolint only parses the
file. It never builds it or pulls an image. :code:`.hadolint.yaml` fails on
level *error* and lowers every other rule that hadolint ships as *error* to
*warning*, so these remain:

- :code:`DL1000`: the Dockerfile cannot be parsed.
- :code:`DL3061`: an instruction before the first :code:`FROM`.
- :code:`DL3023`: :code:`COPY --from` refers to its own stage.
- :code:`DL3011`: an :code:`EXPOSE` port outside 0-65535.
- ShellCheck findings of level *error* in a :code:`RUN`.

When you bump hadolint, check its rule list for new *error* rules and lower
them in :code:`.hadolint.yaml` unless they stop a build.

Advisory
^^^^^^^^

Every finding, with each rule at the level hadolint gives it.
:code:`ci/ci-code/lint/hadolint-quality.yaml` sets :code:`trustedRegistries`, which turns on
:code:`DL3026` (base images only from :code:`docker.io`, :code:`quay.io`,
:code:`registry.k8s.io`, :code:`registry.hzdr.de` and the in-cluster
:code:`local-registry.services.svc.cluster.local:5000`). To silence an
intended finding, put :code:`# hadolint ignore=DL3008` on the line above the
instruction.

Ignored
^^^^^^^

- :code:`DL3007`: the :code:`latest` tag. :code:`local-only/<image>:latest`
  is built in the same build.
- :code:`DL3022`: :code:`COPY --from` an unknown stage. :code:`constraints`,
  :code:`lib` and :code:`charts` are build contexts from kaapana-build.
- :code:`DL3048`: label key format. kaapana-build reads the uppercase
  :code:`IMAGE`, :code:`VERSION` and :code:`BUILD_IGNORE` labels.

.. _code_formatting_helm:

Helm charts
-----------

Charts are linted with `helm lint <https://helm.sh/docs/helm/helm_lint/>`_,
rendered with fake values and validated by
`kubeconform <https://github.com/yannh/kubeconform>`_, all by
:code:`kaapana-build --lint-only`. Chart dependencies are resolved by name, so
:code:`kaapana-build` first assembles the chart tree into
:code:`build/helm-lint/`. The advisory
`kube-linter <https://github.com/stackrox/kube-linter>`_ runs only in the
:code:`lint` mode of :code:`helm_lint.sh`: :code:`kaapana-build --lint-only --no-linting`
assembles the tree, the script renders it into :code:`build/helm-lint/rendered/`
and runs kube-linter on it. A regular :code:`kaapana-build` runs helm lint and
kubeconform too, before packaging, unless :code:`--no-linting` is given. There,
only errors fail.
Configuration: :code:`build_cli/build_cli/configs/fake-values.yaml` and
:code:`ci/ci-code/lint/kube-linter-quality.yaml` (advisory).
Rule reference: `helm lint rules <https://github.com/helm/helm/tree/v4.3.0/pkg/chart/v2/lint/rules>`_
(source code, as :code:`helm lint` has no rule IDs and no rule list),
`kubeconform <https://github.com/yannh/kubeconform#overview>`_,
`kube-linter checks <https://docs.kubelinter.io/#/generated/checks>`_.

.. code-block:: bash

    ci/ci-code/lint/helm_lint.sh validate # validate: [helm]
    ci/ci-code/lint/helm_lint.sh lint     # lint: [helm], advisory
    kube-linter checks list               # every kube-linter check

Scope
^^^^^

- Pre-commit: starts when a staged :code:`Chart.yaml`,
  :code:`requirements.yaml`, :code:`values.yaml` or :code:`templates/` file
  changes. It then checks the whole chart tree, the platform chart and every
  extension collection, but fails only on findings in the charts that contain
  the staged files.
- CI (:code:`validate: [helm]` and :code:`lint: [helm]`): the whole chart
  tree. Each job assembles and renders the tree itself.
- Charts with :code:`ignore_linting: true` in :code:`Chart.yaml` are skipped.

What each tool checks
^^^^^^^^^^^^^^^^^^^^^

- **helm lint** checks each chart's source, before rendering. Every rule has
  a fixed level, error or warning:

  - :code:`Chart.yaml` (:code:`chartfile.go`): errors for a missing or
    invalid name, version (SemVer), :code:`apiVersion`, chart type,
    maintainer, source or icon URL, or dependencies in an apiVersion v1
    chart. Warnings for unknown or duplicate fields and a version that is
    not strict SemVer 2.
  - :code:`values.yaml` (:code:`values.go`): error if it does not parse or
    does not match :code:`values.schema.json`.
  - Templates (:code:`template.go`, :code:`deprecations.go`): errors for a
    template that does not render, a file with a wrong extension, YAML that
    does not parse, a workload without :code:`selector.matchLabels`, and a
    list in :code:`metadata.annotations`. Warnings for a missing
    :code:`templates/` directory, wrong top-level indentation, a resource name
    that breaks the Kubernetes naming rules, and a deprecated or removed
    Kubernetes API.
  - Dependencies (:code:`dependencies.go`): errors for a dependency that is
    listed twice or present in :code:`charts/` but not in
    :code:`Chart.yaml`. Warning for a dependency missing from
    :code:`charts/`.
  - CRDs (:code:`crds.go`): errors for an invalid :code:`crds/` directory or a
    file that is not a valid :code:`apiextensions.k8s.io`
    CustomResourceDefinition.

- **kubeconform** has no rules: it validates every rendered resource against
  the JSON schema of its kind, the Kubernetes schemas for built-in kinds and
  the `CRDs-catalog <https://github.com/datreeio/CRDs-catalog>`_ for custom
  resources. A resource fails for a missing required field, a wrong type or
  value, and, with :code:`-strict`, an unknown field or a duplicate key. A
  kind with no schema fails. :code:`KUBECONFORM_SKIP_KINDS` (comma-separated
  kinds) skips it.

- **kube-linter** checks what the schema cannot: whether the rendered
  resources fit together and follow good practice. It has 63 checks. The
  lists below say which ones Kaapana uses. It is advisory only.

Blocking
^^^^^^^^

Pre-commit fails only on the charts that contain the staged files. CI fails
on every chart.

- :code:`helm lint` errors and warnings.
- kubeconform: every invalid resource.

A :code:`helm lint` run that crashes, or a chart that cannot be rendered with
the fake values, fails in every chart, also in pre-commit.

Advisory
^^^^^^^^

- kube-linter: its 31 default checks, exactly as kube-linter ships them,
  such as missing CPU and memory requests, containers running as root, a
  writable root file system, a probe on a port the container does not expose,
  a Service that selects no pod, a duplicate environment variable or the
  :code:`latest` tag. kube-linter defines this list. Run
  :code:`kube-linter checks list` and look for "Enabled by default: true".
- kube-linter checks that are off by default:

  - Likely bugs: :code:`dangling-ingress`,
    :code:`dangling-horizontalpodautoscaler`,
    :code:`dangling-servicemonitor`, :code:`dangling-networkpolicy`,
    :code:`dangling-networkpolicypeer-podselector`, and
    :code:`env-value-from` (a Secret or ConfigMap that is not part of the
    chart, though it may still be created at runtime).
  - Security: :code:`privileged-ports`, :code:`read-secret-from-env-var`,
    :code:`writable-host-mount`, :code:`unsafe-proc-mount`,
    :code:`exposed-services` (NodePort or LoadBalancer),
    :code:`use-namespace` (the :code:`default` namespace), and the RBAC
    checks :code:`cluster-admin-role-binding`, :code:`access-to-secrets`,
    :code:`access-to-create-pods` and :code:`wildcard-in-rules`.

To accept a kube-linter finding for one resource, annotate it with
:code:`ignore-check.kube-linter.io/<check>: "<reason>"`.

:code:`lint: [helm]` writes the kube-linter findings to the Code Quality report.
Each finding points to the source template. :code:`validate: [helm]` publishes
the :code:`helm lint` errors and kubeconform results to the merge request test
tab as JUnit reports.

Not selected
^^^^^^^^^^^^

These kube-linter checks are off by default and not used, because they assume
a multi-node production cluster or a specific organisation's policy, or
duplicate another tool:

- :code:`minimum-three-replicas`, :code:`hpa-minimum-three-replicas`,
  :code:`no-node-affinity`, :code:`no-rolling-update-strategy`,
  :code:`priority-class-name`, :code:`dnsconfig-options`: high-availability
  and scheduling setup. Kaapana usually runs on one node.
- :code:`non-isolated-pod`, :code:`default-service-account`,
  :code:`restart-policy`: cluster policy choices.
- :code:`no-liveness-probe`, :code:`no-readiness-probe`: most Kaapana
  containers have no probes yet. A probe on a wrong port is still reported.
- :code:`required-annotation-email`, :code:`required-label-owner`: examples
  for organisation-specific metadata.
- :code:`sorted-keys`: key order is decided by Helm's rendering, not by the
  templates.
- :code:`schema-validation`: kubeconform already validates the schemas.
- :code:`scc-deny-privileged-container`: OpenShift only.
