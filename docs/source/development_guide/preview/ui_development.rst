.. _ui_development:

======================
Kaapana UI Development
======================

This page orients developers building or extending a Kaapana web UI: how the
frontend is composed, how views plug into the platform menu and project
scoping, how code is shared between views, and how the UI is tested. It is the
entry point — the integration contracts themselves are documented on
:ref:`landing_page_integration` and :ref:`project_scoping`.


Architecture: one shell, many views
===================================

The Kaapana frontend is not a monolith. A thin **shell**, ``portal-ui``
(``services/base/portal-ui``), owns the chrome: the navigation drawer (built
at runtime from ``/portal-api/menu``), the project selector, and the settings
and notification dialogs. The view behind each menu entry is rendered inside a
same-origin iframe (``src/views/IframeHost.vue``). The shell contains no view
code — it talks to the embedded views only through the document URL
(``/project/<short_id>/…``), ``localStorage``, and a small ``postMessage``
protocol.

Each **view** is a self-contained single-page app under
``services/base/<view>-ui/docker/files`` (each was extracted from the former
monolithic landing page, which no longer exists). Every view is its own
Vue 3 + Vuetify 3 + Vite app with its own
``package.json``, its own Dockerfile (a node build stage, then an unprivileged
nginx image serving the static ``dist/``), and its own mock-backed Playwright
e2e suite (see :ref:`ui_testing`). Views are deployed as independent
containers and discovered by the shell at runtime via Ingress annotations, so
adding, changing, or removing a view never requires touching the shell.


The default UI stack
====================

New Kaapana UIs use one stack — the one the shell and every view are built
with:

- **Vue 3** single-file components written in **TypeScript** with the
  Composition API and ``<script setup>``; ``vue-tsc`` type-checks as part of
  ``npm run build``.
- **Vuetify 3** as the component library; shared components and theming live
  in :ref:`base_ui_package`.
- **Vite** for the dev server and the production build, **Pinia** for state
  where a store is warranted.
- A multi-stage Dockerfile: a node build stage, then an unprivileged
  **nginx** image serving the static ``dist/``.
- A mock-backed **Playwright** e2e suite (see :ref:`ui_testing`).

Stick to this stack for new UI work; a deviation should be a deliberate,
documented exception.


Package management: npm only
============================

All first-party UIs are built with **npm** — yarn is not used for any Kaapana
frontend:

- Every app commits exactly one lockfile, ``package-lock.json``, next to its
  ``package.json``. A second lockfile (``yarn.lock``) means two resolvers
  with two diverging dependency trees.
- Dockerfiles install with ``npm ci``, never ``npm install``, pinning the npm
  version first where the base image's node supports it:

  .. code-block:: docker

     RUN npm install -g npm@11.16.0 && npm ci

  ``npm ci`` installs the lockfile exactly and **fails** when
  ``package.json`` and the lockfile disagree, so the image build catches
  dependency drift instead of silently resolving to different versions than
  local dev.
- After changing dependencies in ``package.json``, run ``npm install``
  locally and commit the updated lockfile together with that change.
- Do not use ``resolutions`` — it is yarn-only and npm silently ignores it.
  To pin a transitive dependency, use npm's ``overrides``.

The only exceptions are vendored third-party apps built from their upstream
sources with the upstream toolchain (``ohif-viewer``, ``slim-viewer``,
``os-dashboards``, the selkies frontend in ``base-desktop``).


Getting a view into the menu
============================

:ref:`landing_page_integration` is the reference for everything between a
deployed view and the shell: the ``kaapana.ai/ui.*`` Ingress annotations that
turn an Ingress into a menu entry (label, section, icon, ordering, iframe vs.
tab target), menu count badges, the ``localStorage["settings"]`` contract, and
the messages a view exchanges with the shell — ``kaapana:view-dirty`` to report
unsaved changes so the shell warns before discarding them, and
``kaapana:project-switch`` / ``kaapana:navigate`` to ask the shell to change
project or open another view without reloading it. It includes a complete
worked example (Service + Middleware + annotated Ingress) and a
troubleshooting section.

:ref:`project_scoping` describes how the selected project travels in the URL
(``/project/<id>/…``), how the gateway authorizes the request, strips the
prefix, and hands services a trusted ``Project`` header — and what a view must
do to participate: declare the extra ``IngressRoute``, derive its scope from
its own document URL, and prefix its API calls with a small axios
interceptor.


.. _base_ui_package:

Shared code: ``@kaapana/base-ui``
=================================

``services/base/base-ui/docker/files`` holds ``@kaapana/base-ui``, a small
shared library for components and utilities that would otherwise be
copy-pasted into every view. It currently exports:

- ``httpClient`` / ``httpClientWithoutTimeout`` — the shared axios instances.
  Their request interceptor adds the ``/project/<short_id>`` prefix to
  project-scoped services, so views request plain paths (see
  :ref:`project_scoping`).
- ``getProjectSlug()`` / ``getProjectBase()`` — the selected project as it
  travels in the document URL.
- ``switchProject(slug)`` — ask the shell to switch projects
  (:ref:`kaapana:project-switch <project_switch_message>`).
- ``navigateShell(path)`` — ask the shell to open another view
  (:ref:`kaapana:navigate <shell_navigate_message>`).
- ``postViewDirty(dirty)`` — the wrapper for the shell's
  :ref:`unsaved-changes protocol <view_dirty>`.
- ``useAuthStore`` / ``AuthService`` — authentication state and the
  dev-vs-production token sources.
- ``useProjectStore`` — the user's projects, resolved against the URL slug.
- ``kaapanaApiService`` — the remaining shared backend calls.
- ``kaapanaThemeLight`` / ``kaapanaThemeDark`` (+ their name constants) and
  ``useShellSettings()`` — the Vuetify themes and the
  ``localStorage["settings"]`` sync.

The shared workflow-execution form is a **subpath** export,
``@kaapana/base-ui/workflow-execution``, deliberately kept off the main entry so
views that do not need it never install its ``vjsf`` peer dependency.

**Every** dependency of the library is a ``peerDependency`` and is never
bundled — the consuming view provides them all. Five are required
(``vue``, ``vuetify``, ``axios``, ``@kyvg/vue3-notification``, ``pinia``) and
``@koumoul/vjsf`` is optional, installed only by consumers of the
``./workflow-execution`` entry. This is what makes the ``resolve.dedupe`` list
below a five- (or six-) name list rather than a two-name one.

What belongs there — and what does not
--------------------------------------

Only small, stable, genuinely shared pieces go into ``base-ui``. Everything
view-specific stays in the view, even when that means similar code exists in
two views — the per-view duplication is deliberate: it keeps every view
independently buildable and testable and avoids premature abstraction.
Extract into ``base-ui`` only once a piece is needed by several views *and*
is small and stable enough that its API will not churn.

Dev loop
--------

The library must be built once before working on any consumer — views import
its built ``dist/`` output, not its sources:

.. code-block:: bash

   cd services/base/base-ui/docker/files
   npm ci
   npm run build        # emits dist/ — what consumers import

After that, the usual per-view loop works unchanged from the view's
``docker/files`` directory: ``npm ci && npm run dev``,
``npx playwright test``, ``npm run build``.

.. warning::

   Re-run ``npm run build`` after **every** change to ``base-ui``'s ``src/``.
   Consumers resolve the package through an npm symlink and silently keep
   importing the stale ``dist/`` — nothing fails, the change is just not
   there.

Components can be developed in isolation with Storybook (dev-only: not
deployed and not exercised in CI):

.. code-block:: bash

   npm run storybook    # http://localhost:6006

Adding a shared component
-------------------------

1. Add the source under ``src/`` (components in ``src/components/``, plain
   helpers in ``src/utils/``).
2. Export it from ``src/index.ts``, the main entry — unless it pulls the
   optional ``@koumoul/vjsf`` peer, in which case it belongs on the
   ``./workflow-execution`` subpath entry (``src/workflowExecution.ts``)
   instead, so views that do not need ``vjsf`` never have to install it.
3. Add a ``*.stories.ts`` next to it so it shows up in Storybook.
4. ``npm run build``.

Keep every runtime dependency in ``peerDependencies`` (never
``dependencies``): the library must always run against the consumer's copies.
A new peer must be added to the ``resolve.dedupe`` list of every consumer at
the same time — see the warning below.
The package is ``private`` and never published — it is consumed only through
the ``file:`` link described next, so there is no registry versioning to
manage.

Consuming from a view
---------------------

A view declares the library as a relative ``file:`` dependency. The path is
relative to the view's ``docker/files`` directory and is the same in the repo
and inside the Docker build:

.. code-block:: json

   {
     "dependencies": {
       "@kaapana/base-ui": "file:../../../base-ui/docker/files"
     }
   }

``npm install`` creates a symlink in ``node_modules``, and imports work as for
any package:

.. code-block:: typescript

   import { postViewDirty, useShellSettings } from '@kaapana/base-ui'

The view's ``vite.config.ts`` **must** dedupe **all** of the peer dependencies —
``dist/`` externalizes every one of them, so an omitted name is a build failure,
not a silent duplicate:

.. code-block:: typescript

   resolve: {
     dedupe: ['vue', 'vuetify', 'axios', '@kyvg/vue3-notification', 'pinia'],
   }

A view that imports the ``./workflow-execution`` entry appends
``'@koumoul/vjsf'``; the others must not, since they do not install that
optional peer. List **package names** only — a subpath import
(``vuetify/components``) is covered by its package's entry.

Because the package is symlinked, imports inside it would otherwise resolve
against ``base-ui``'s *own* ``node_modules``: locally that loads a second copy
of each peer into the app, and inside the Docker image that directory does not
exist at all (only ``package.json`` and ``dist/`` are copied), so the build
fails outright — ``Rollup failed to resolve import "pinia" from
…/dist/index.js``. ``dedupe`` forces both cases to the consumer's copies. The
authoritative list lives in ``services/base/base-ui/docker/files/README.md``.

.. warning::

   Because every view pulls ``base-ui`` in through this ``file:`` link, a
   change to ``base-ui``'s ``package.json`` **dependencies** invalidates
   *every* consumer's ``package-lock.json``. ``npm ci`` then **fails** in all
   view image builds until each consumer lockfile is regenerated — run
   ``npm install`` in every consumer's ``docker/files`` with the
   container-pinned ``npm@11.16.0`` and commit the updated lockfiles alongside
   the ``base-ui`` change.

Docker build chain
------------------

The library image (``services/base/base-ui/docker/Dockerfile``) is a
build-stage-only base image: it carries ``LABEL REGISTRY="local-only"``, is
tagged ``local-only/base-ui:latest``, and is never pushed to a registry.
Consumer Dockerfiles start with

.. code-block:: docker

   FROM local-only/base-ui:latest AS base-ui

and copy the built library (``package.json`` + ``dist/``) into the image at
the same ``/kaapana/base-ui/docker/files`` path it has relative to the repo,
so the ``file:`` dependency resolves identically in-image and in the source
tree.

``kaapana-build`` reads the ``FROM`` line, recognizes the ``local-only``
dependency, and builds ``base-ui`` first automatically. When building a
single view with plain ``docker build``, build the library image once
yourself:

.. code-block:: bash

   docker build -t local-only/base-ui:latest services/base/base-ui/docker
   docker build services/base/workflow-execution-ui/docker

Deploying a new view
--------------------

Writing the app and annotating its Ingress is not enough — a chart nothing
depends on is never installed. Add the view's chart to the services-namespace
chart's dependency list:

.. code-block:: yaml

   # platforms/kaapana-platform-chart/deps/services-namespace/requirements.yaml
   dependencies:
     ...
     - name: <view>-ui
       version: 0.0.0

Without this entry the image is built, the annotations are correct, and the
view simply never reaches the cluster.

The view's Ingress path also needs an OPA grant, and so does the shell route
its menu entry navigates to — see
:ref:`the troubleshooting section <landing_page_troubleshooting>` of
:ref:`landing_page_integration`, which describes both halves.

CI
--

The ``ui_e2e_tests`` job in ``ci/pipeline/unit-tests.yml`` runs one matrix entry
per app. Before installing an app it checks the app's ``package.json`` for
``"@kaapana/base-ui"`` and, if present, first runs ``npm ci && npm run build``
in the library — so a consumer gets the library built in CI automatically,
simply by declaring the ``file:`` dependency.

That automation applies **within** an existing matrix entry; the matrix itself
is a hard-coded list. A new view is not tested at all until it is added to it:

.. code-block:: yaml

   # ci/pipeline/unit-tests.yml
   ui_e2e_tests:
     parallel:
       matrix:
         - APP:
             - portal-ui
             ...
             - <view>-ui

Pick the app's Playwright port from the registry in :ref:`ui_testing` (one port
per app, ``--strictPort``) so suites can keep running in parallel.

The same file carries ``ui_unit_tests``, a single (non-matrix) job running
``portal-ui``'s vitest suites — it is the only app with a ``test:unit`` script.


.. _ui_testing:

Testing
=======

Every app — the shell and each view — ships a Playwright end-to-end suite
under ``docker/files/tests/e2e``. The suites are **mock-backed**: a
``fixtures/mock-backend.ts`` intercepts the app's backend calls in the browser
with Playwright's ``page.route`` and serves fixture data whose shapes are
imported from the app's own ``src/`` types, so contract drift fails
type-check instead of silently passing. No cluster or backend is needed to
run them.

Each suite starts its app's own Vite server (the dev server locally, a
``preview`` of the production build in CI) on a fixed per-app port —
``portal-ui`` on 4300, the views on 4301–4309 — so all suites can run in
parallel on one machine. Run a suite from the view's ``docker/files``
directory with ``npx playwright test`` (build ``base-ui`` first if the view
consumes it). CI runs the same suites in the ``ui_e2e_tests`` matrix job.

``portal-ui`` additionally ships vitest unit suites under
``src/**/__tests__`` for the pieces that are awkward to reach through the
browser (the project-prefix rewriting in ``api/http.ts``, the OPA menu filter,
the stores). Run them with ``npm run test:unit``; CI runs them in
``ui_unit_tests``.
