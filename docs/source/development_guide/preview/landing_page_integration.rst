.. _landing_page_integration:

===========================================
Adding your Application to the Kaapana Menu
===========================================

The Kaapana landing page (the ``portal-ui`` shell) builds its navigation menu by
**discovering Kubernetes Ingresses** at runtime. There is no central menu
configuration file: any Ingress annotated with ``kaapana.ai/ui.name`` *is* a
menu entry.

A small FastAPI service, ``portal-api``, lists Ingresses across **all
namespaces**, parses their ``kaapana.ai/ui.*`` annotations into a menu
structure, and serves it at ``/portal-api/menu``. The shell fetches that
endpoint and renders the drawer. To add your application to the menu you
therefore only need to ship an Ingress with the right annotations — no change
to the shell or to ``portal-api`` is required.

.. note::

   Discovery is cluster-wide. Whether a given user actually *sees* and can
   *reach* an entry is enforced separately by OPA (see
   :ref:`landing_page_troubleshooting`).


Annotation Reference
====================

Entry annotations
-----------------

These annotations describe a single menu entry. They are read only from an
Ingress that carries ``kaapana.ai/ui.name``.

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Annotation
     - Meaning
   * - ``kaapana.ai/ui.name``
     - **Required.** The label shown in the menu. Its presence is what opts the
       Ingress into discovery; an empty value skips the entry.
   * - ``kaapana.ai/ui.section``
     - Section id this entry belongs to. Omit it to place the entry at the top
       level of the menu.
   * - ``kaapana.ai/ui.icon``
     - Material Design Icon name (e.g. ``mdi-view-dashboard``).
   * - ``kaapana.ai/ui.order``
     - Integer (as a string) used for sorting; smaller sorts first. Defaults to
       ``1000``. A non-integer value logs a WARNING and falls back to ``1000``.
   * - ``kaapana.ai/ui.path``
     - Link / iframe target. Must be **platform-relative** (see the note below
       the table); otherwise it is ignored (WARNING) and the entry falls back to
       the Ingress' first rule path. If neither a valid ``ui.path`` nor a rule
       path exists, the entry is skipped.
   * - ``kaapana.ai/ui.target``
     - ``iframe`` (default) embeds the app in the shell; ``tab`` opens it in a
       new browser tab. Use ``tab`` for apps that refuse to be framed. Any other
       value logs a WARNING and falls back to ``iframe``. This is one of the two
       values that are **not** whitespace-stripped, so ``" tab"`` is such an
       "other value".
   * - ``kaapana.ai/ui.default``
     - Set to ``"true"`` on exactly one entry platform-wide to make it the view
       shown at ``/``. If more than one entry claims it, the one on the
       lexicographically smallest ``(namespace, ingress-name)`` wins — the same
       ordering as the section merge rule below — and the rest are cleared with
       a WARNING.
   * - ``kaapana.ai/ui.id``
     - Route slug used in ``/web/<section>/<id>``. Defaults to the slugified
       ``ui.name``. Must be unique per ``(section, id)`` pair; a duplicate is
       skipped with a WARNING.
   * - ``kaapana.ai/ui.project``
     - How the view consumes the selected project (see
       :ref:`project_scoping`). ``path``: the shell prefixes the iframe URL
       with ``/project/<short_id>`` and reloads the iframe on a project
       switch. ``none`` (default): project-agnostic. Any other value logs a
       WARNING and falls back to ``none``. Like ``ui.target``, this value is
       **not** whitespace-stripped.
   * - ``kaapana.ai/ui.badge-path``
     - Platform-relative path (otherwise ignored with a WARNING) the shell polls
       for a small count badge on this entry. Empty means no badge. See
       :ref:`menu_count_badges`.
   * - ``kaapana.ai/ui.dev-links``
     - Comma-separated ``Label=/path`` pairs pointing at the API docs of the
       services behind this entry, surfaced in the drawer only while *Dev Mode*
       is on (Settings). Each path must be platform-relative; a pair that is
       malformed or whose path is not logs a WARNING and is skipped.
       Empty or absent means no dev links. Each link is authorization-checked
       on its own, so a user only sees the ones their roles can reach. Example:
       ``"Workflow API=/workflow-api/docs,Kaapana Backend=/kaapana-backend/docs"``.

.. note::

   **"Platform-relative" is stricter than "starts with ``/``".** ``ui.path``,
   ``ui.badge-path`` and every ``ui.dev-links`` path are rejected unless they
   address this platform and nothing else, so a protocol-relative ``//host/x``,
   a backslash variant ``/\host/x`` and any tab-, newline- or CR-smuggled
   authority are refused even though they start with a slash.

   Every annotation value is whitespace-stripped **except** ``ui.target`` and
   ``ui.project``, where a stray leading space therefore reaches the
   value check and triggers the fallback.

   Keys outside the fourteen listed here are ignored with a WARNING — but only
   on Ingresses that carry ``ui.name``, since nothing else is inspected at all.

Section annotations
-------------------

These annotations describe the *section* an entry belongs to. They are read from
Ingresses that carry both ``ui.name`` and ``ui.section``, so there is no separate
"section-only" resource: the metadata rides on one or more member entries. By
convention one member acts as the "anchor" and declares them.

Note that a member's section metadata is registered **before** its own entry is
parsed, so it still contributes even when that entry is then skipped — for a
blank ``ui.name``, an unusable path or a duplicate ``ui.id``. A section can
therefore be labelled and ordered by an Ingress that contributes no visible
entry, which is a useful escape hatch but an easy surprise when debugging.

.. list-table::
   :header-rows: 1
   :widths: 26 74

   * - Annotation
     - Meaning
   * - ``kaapana.ai/ui.section-label``
     - Display label for the section. If no member declares one, the section id
       is used with its first letter capitalized.
   * - ``kaapana.ai/ui.section-icon``
     - Material Design Icon name for the section.
   * - ``kaapana.ai/ui.section-order``
     - Integer (as a string) used to sort the section among top-level items.
       Defaults to ``1000``; a non-integer value logs a WARNING and also counts
       as ``1000``.

Merge rule
----------

When several member Ingresses declare the same section, values are merged
deterministically: for each field, the value from the lexicographically
smallest ``(namespace, ingress-name)`` that declares a non-empty value wins.
The section order is the numeric minimum over all declared ``section-order``
values — an unparseable one is **not** excluded, it enters the minimum as
``1000``, so a typo on one member can pull a section that every other member
puts at ``2000`` up to ``1000``.


Worked Example
==============

The following manifests add a fictional application ``my-app`` to the
``system`` section. They follow the same pattern Kaapana's own views use (a
``ClusterIP`` Service, a Traefik strip-prefix ``Middleware``, and an annotated
``Ingress``). Adjust the namespace to your deployment's services namespace.

.. code-block:: yaml

   ---
   apiVersion: v1
   kind: Service
   metadata:
     name: my-app-service
     namespace: services
     labels:
       app.kubernetes.io/name: my-app-service
   spec:
     selector:
       app.kubernetes.io/name: my-app
     ports:
       - name: http
         port: 5000
         targetPort: 5000
     type: ClusterIP
   ---
   apiVersion: traefik.io/v1alpha1
   kind: Middleware
   metadata:
     name: strip-prefix-my-app
     namespace: services
   spec:
     stripPrefix:
       prefixes:
       - /my-app
   ---
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: my-app-ingress
     namespace: services
     annotations:
       traefik.ingress.kubernetes.io/router.entrypoints: websecure
       traefik.ingress.kubernetes.io/router.middlewares: services-strip-prefix-my-app@kubernetescrd
       kubernetes.io/ingress.global-static-ip-name: "kubernetes-ingress"
       # Menu discovery: this Ingress becomes a menu entry.
       kaapana.ai/ui.name: "My App"
       kaapana.ai/ui.section: "system"
       kaapana.ai/ui.icon: "mdi-cog-outline"
       kaapana.ai/ui.order: "50"
       kaapana.ai/ui.id: "my-app"
       # Section metadata (this entry acts as the section anchor).
       kaapana.ai/ui.section-label: "System"
       kaapana.ai/ui.section-icon: "mdi-server"
       kaapana.ai/ui.section-order: "90"
   spec:
     rules:
     - host:
       http:
         paths:
         - path: /my-app
           pathType: ImplementationSpecific
           backend:
             service:
               name: my-app-service
               port:
                 number: 5000

Because no ``ui.path`` is given, the entry links to the Ingress' first rule
path (``/my-app``). The strip-prefix Middleware removes ``/my-app`` before the
request reaches the backend, so the application is served from its own root.


.. _menu_count_badges:

Count Badges
============

An entry can carry a small count badge in the menu (for example, the number of
tasks awaiting input). Opt in with a single annotation pointing at an endpoint
that returns the count:

.. code-block:: yaml

   kaapana.ai/ui.badge-path: "/kube-helm-api/pending-applications-count"

``portal-api`` copies the value into the entry's ``badgePath`` (empty when the
annotation is absent, or when its value is not **platform-relative** — the
stricter check described in the note under *Entry annotations* above, which
also rejects ``//host``, ``/\host`` and any tab-, newline- or CR-smuggled
authority even though they start with a slash). The endpoint must answer with
JSON of the shape ``{"count": <integer>}``.

**Counts are project-scoped.** The shell fetches ``badgePath`` through the same
axios interceptor as every other project call, so the URL is rewritten to
``/project/<short_id>/…`` from the current document URL and the backend receives
the enriched ``Project`` header. Make the count project-specific: an unscoped
request (no ``Project`` header) should return ``0``.

**When it refreshes.** Counts are polled on every menu poll (~15 s) and are
re-fetched immediately on a project switch. On a switch the previous project's
counts are dropped first, so a stale count never lingers under the wrong
project; a failed re-poll therefore hides the badge rather than showing the old
value. A failed *periodic* poll instead keeps the last known count (no flicker
on a transient error).

The drawer renders the badge on the entry itself, and a collapsed section shows
the **sum** of its entries' badges on the section header, so the count is
visible before the section is expanded.


Shell-to-View Communication via localStorage
============================================

Menu entries are rendered inside an iframe on the same origin as the shell, so
the shell and all embedded views share ``window.localStorage``. The shell uses
this to pass UI state to views without any API round trip:

- ``localStorage["settings"]`` — a JSON object owned by the shell. It is
  seeded on login (defaults merged with the user's persisted settings from
  ``/kaapana-backend/settings``) **before** the first iframe mounts, and
  rewritten whenever the user changes a setting. Views may read it
  synchronously at startup.

The **selected project is deliberately not part of this contract**: it travels
in the document URL. Views declared ``kaapana.ai/ui.project: "path"`` are
served under ``/project/<short_id>/<view>/`` and derive their scope from
``window.location`` (see :ref:`project_scoping`); a switch reloads the iframe
under the new prefix. This keeps every browser tab independently scoped —
shared storage would make concurrent tabs on different projects fight over one
global selection. (The shell still keeps ``localStorage["project"]`` as its own
cross-session default for tabs opened without a project prefix; views must not
read it.)

Keys currently used by views:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Key
     - Type
     - Meaning
   * - ``darkMode``
     - boolean
     - Whether the dark theme is active. Views should apply it to their own
       UI toolkit (e.g. ``$vuetify.theme.dark`` in Vue 2, or the Vuetify 3
       theme name).
   * - ``datasets`` / ``workflows``
     - object
     - View-specific defaults (gallery layout, per-DAG form defaults) used by
       the dataset and workflow views.

**React to changes.** When the shell writes one of these keys, the browser
fires a ``storage`` event in every *other* same-origin document — i.e. in each
embedded view. The shell **never reloads** on a settings change; views are
expected to update themselves:

.. code-block:: javascript

   function applyShellSettings() {
     const settings = JSON.parse(localStorage["settings"] || "{}");
     // apply settings.darkMode etc. to your UI toolkit
   }
   applyShellSettings();
   window.addEventListener("storage", (e) => {
     if (e.key === "settings") applyShellSettings();
   });

Apply values live where possible (as with ``darkMode``). For settings that are
only read at component creation, a pragmatic alternative is to remount the
view's component tree, e.g. by bumping a ``:key`` on the root ``router-view``
(this is what the shipped views do). Note that the ``storage`` event
does **not** fire in the document that performed the write — only in the
embedded views.


.. _view_dirty:

Reporting Unsaved Changes (``kaapana:view-dirty``)
==================================================

Leaving a view — navigating to another menu entry, switching the project
(which reloads the iframe under the new ``/project/<short_id>`` prefix), or
the shell's refresh button — discards the view's in-memory state. Before doing
so the shell can warn the user — but only if the view tells it there is
something to lose. A view opts in by posting a ``kaapana:view-dirty`` message
to its parent whenever its dirty state changes:

.. code-block:: javascript

   // WHY window.location.origin (not "*"): the shell only trusts same-origin
   // messages; a standalone (non-iframed) view just posts to itself, harmlessly.
   function postViewDirty(dirty) {
     window.parent.postMessage(
       { type: "kaapana:view-dirty", dirty }, window.location.origin,
     );
   }

The shell validates ``event.origin === location.origin`` and the message
``type`` before storing the flag. When it is set, any action that would reload
the iframe shows an "Unsaved changes" confirm dialog ("Stay" / "Leave view")
before committing the navigation or refresh.

**A reloaded view starts clean.** The shell resets the flag to ``false`` on
every iframe ``src`` change and on every ``load`` (including in-iframe
navigation), so the view never has to re-clear it after a reload. Within a live
session the view reports both edges — ``true`` when state becomes dirty,
``false`` when it is cleared.

**Only report state that a reload would lose.** Report in-memory input (search
text, filters, an in-progress form). State that survives a reload — anything
persisted to ``localStorage``, such as the gallery's tag selection — must
**not** be reported, or the user would be warned about changes that are not
actually lost.

The helper above ships as ``postViewDirty`` in the shared ``@kaapana/base-ui``
package (see :ref:`base_ui_package`). The shipped views wire it from a single
watcher: the gallery view (``Search.vue``) reports whenever a search query or
filter is active, and the workflow-execution view (``WorkflowExecution.vue``)
reports once a DAG has been picked by the user or the form has been edited
(programmatic defaults and the boot-time single-DAG auto-select do not count).


.. _shell_navigate_message:

Opening Another View (``kaapana:navigate``)
===========================================

A view that links into another view — the home view's capability cards, for
example — must **ask the shell** rather than set ``window.top.location``:

.. code-block:: javascript

   window.parent.postMessage(
     { type: "kaapana:navigate", path: "/web/workflows/workflows" },
     window.location.origin,
   );

``path`` is a shell route addressed the way the menu addresses it:
``/web/<section>/<id>``, or ``/web/-/<id>`` for a top-level entry. A leading
``/project/<short_id>`` is accepted and ignored — the shell always resolves
against the current project.

On receipt the shell resolves the path against **the menu this user can
actually see**, and then either:

* pushes the route with ``router.push`` — so the
  :ref:`unsaved-changes confirm <view_dirty>` runs first and only the iframe
  reloads; or
* opens a **"View unavailable"** dialog naming the requested path, when the
  entry does not exist (its extension is not installed) or the user's role may
  not open it.

That second branch is the reason to prefer the message. A top-level navigation
to an unresolvable entry is silently rewritten to the project home by the
router guard, which reads to the user as a dead link.

The helper ships as ``navigateShell`` in ``@kaapana/base-ui`` (see
:ref:`base_ui_package`); standalone it falls back to a plain top-level
navigation.

.. _project_switch_message:

Switching the Project From a View (``kaapana:project-switch``)
==============================================================

A view that offers project switching (the home view lists the user's projects)
must **ask the shell** rather than navigate the top window itself:

.. code-block:: javascript

   // Same origin rule as view-dirty: the shell only trusts same-origin messages.
   window.parent.postMessage(
     { type: "kaapana:project-switch", slug }, window.location.origin,
   );

``slug`` is the target project's ``short_id``. The shell validates the origin,
ignores a slug that is not in the user's project list, then swaps the
``/project/<short_id>`` prefix on the **current** route and navigates with
``router.push`` — exactly what its own project selector does.

**Why not just set** ``window.top.location``? A hard top-level navigation
technically works, but it skips two things the shell owns:

* the :ref:`view-dirty <view_dirty>` confirm never runs, so a view with unsaved
  changes loses them without warning;
* the whole shell bundle is re-downloaded instead of only the iframe reloading.

The helper ships as ``switchProject`` in ``@kaapana/base-ui`` (see
:ref:`base_ui_package`). It posts the message when embedded and falls back to a
plain top-level navigation when the view is served standalone, where there is
no shell to ask — posting to itself would silently do nothing.

.. _landing_page_troubleshooting:

Verification and Troubleshooting
================================

**Inspect the assembled menu** directly from the API:

.. code-block:: bash

   curl https://<host>/portal-api/menu

The response is the JSON the shell renders. If your entry is missing, check the
following.

**Read the service log.** Malformed annotations never fail the whole menu: the
offending entry is skipped or defaulted, and a WARNING is written to the
``portal-api`` pod log. Common causes are an empty ``ui.name``, a ``ui.path``
that does not start with ``/``, a non-integer ``ui.order``, or a duplicate
``ui.id`` within a section.

**Entry visibility is enforced by OPA, and an entry needs TWO grants.** Both go
into ``services/kaapana-admin/auth-backend/auth-backend-chart/files/data.rego``,
in the role lists the entry should be reachable for:

1. **The Ingress path** (``ui.path``, e.g. ``^/<view>-ui``). Without it the
   menu filter hides the entry and the iframe request is refused.
2. **The shell route** the entry navigates to, ``/<section>/<id>`` (or
   ``/<id>`` for a top-level entry). The canonical shell URL is
   ``/project/<short_id>/<section>/<id>``, and auth-backend strips the
   ``/project/<short_id>`` prefix before the policy sees it, so the string to
   grant is the *unprefixed* one — ``^/<section>/<id>`` — not the URL in the
   address bar.

Granting only the first is the easy mistake, because it does not fail where you
are looking: in-app navigation is a pushState within the shell and never reaches
the gateway, so the entry works for the whole session. The 403 appears only on
the **first reload, bookmark or shared deep link** of that URL — and then for
the one user who has the Ingress grant but not the route grant.

.. note::

   **The menu filter is client-side, and it can only see role grants.** The
   shell decides visibility by evaluating the entry's ``ui.path`` against
   ``endpoints_per_role`` from ``GET /kaapana-backend/open-policy-data``. The
   claim rules in ``auth-policies.rego`` (``kaapana.ai/backend``,
   ``kaapana.ai/applications``, …) are rules rather than data, so they are absent
   from that document and invisible to the filter — while in this platform most
   of what a view can actually *do* is granted exactly that way. A visible entry
   therefore means "your roles may load this app", never "your grants make this
   view work", and no client-side gate can close the gap: keying visibility on
   the claim-granted call instead evaluates **false** for the very users who hold
   the claim, hiding a working view from them. A view whose calls are
   claim-granted must therefore surface its own 403s. Closing the gap properly
   needs a server-side answer — the gateway's OPA evaluation exposed as a
   "may I call this?" probe — which the platform does not have today.

Verify both legs for every role that should reach the entry, for example:

.. code-block:: bash

   opa eval --v0-compatible -b files -i input.json 'data.httpapi.authz.allow'

with ``input.requested_prefix`` set to the Ingress path and then to the shell
route.
