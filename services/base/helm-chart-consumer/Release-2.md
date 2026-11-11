# Helm Chart Consumer: decisions for Release 2

This document records what Release 2 adds to the MVP of the Helm Chart Consumer. Read [MVP.md](MVP.md) first. This document does not repeat it.

- The sections have the headings of [MVP.md](MVP.md) where they extend a section of it. Each of them starts with a link to that section.
- A table has the columns of the table that it extends, and holds only the rows that Release 2 adds or changes.
- **Added** marks a statement that is new in Release 2. **Changed** marks a statement that replaces one of the MVP.
- The sources and the markers *(proposed)* and *(to be decided)* are the same as in [MVP.md](MVP.md).
- [api-mock-release-2/](api-mock-release-2/) proposes the routes and models of Release 2. It holds everything of [api-mock/](api-mock/), and what this document adds.

## Scope

Extends [Scope](MVP.md#scope).

Release 2 adds these functions:

- A release can be updated: its version, its parameters, or both ([Stories 11.2][s11.2], [11.3][s11.3], [11.4][s11.4]).
- An application can be deployed platform-wide, once for all projects ([Story 9.1][s9.1]).
- A kaapana-system-admin lists the releases of all projects ([Story 3.4][s3.4]).
- A release reports its Kubernetes objects, pods and events.
- A workflow deploys an application and waits for the user ([Epic 7][e7]).
- The charts of the platform are helm-chart contents, and the consumer deploys them.
- A wrapper of a public chart can map platform values and patch the rendered chart.
- The consumer labels its helm releases.
- A chart gets only the values under `global.kaapana`. The legacy `global` block is no longer passed.
- An application gets the credentials of a technical user of its project, and no longer the passwords of the platform ([Story 4.5][s4.5]).

With these functions, the Helm Chart Consumer takes over the tasks of kube-helm:

| Task of kube-helm | Caller | In Release 2 |
|---|---|---|
| It installs the chart `project-namespace` for every project. | AII | AII deploys a release of a platform content. See [Charts that other services install](#charts-that-other-services-install-proposed). |
| It pulls images with the chart `pull-docker-chart`. | base-installer | The base-installer deploys a release of a platform content. See [Charts that other services install](#charts-that-other-services-install-proposed). |
| It installs the `preinstall_extensions` at platform deploy. | An init job of kube-helm | A bootstrap job registers and deploys them. See [Charts at platform deploy and charts from the legacy page](#charts-at-platform-deploy-and-charts-from-the-legacy-page-proposed). |
| It serves the applications that workflows start. | Workflows | A workflow origin and a route to finish the step. See [Interactive workflows](#interactive-workflows). |
| It keeps the releases that were installed from the legacy page. | kaapana-system-admin | The upgrade reports them. See [Charts that were installed before 0.8.0](#charts-that-were-installed-before-080). |

The ticket wants to remove the legacy system in 0.8.0. kube-helm can only be removed when all rows of this table are implemented.

## Words of the ticket and words of the concept

Extends [Words of the ticket and words of the concept](MVP.md#words-of-the-ticket-and-words-of-the-concept).

| The ticket says | The concept says | Stories |
|---|---|---|
| Update | **Added.** Update a release: its version, its parameters, or both | [11.2][s11.2], [11.3][s11.3], [11.4][s11.4] |

## Interface of the service

Extends [Interface of the service](MVP.md#interface-of-the-service).

### Extension Manager

**Added.** The platform registers its own contents with the same routes, without an extension. See [Charts that other services install](#charts-that-other-services-install-proposed).

### Application page

| Route | What it does |
|---|---|
| `GET /v1/releases/{id}/status` | **Added.** Returns the Kubernetes objects, pods, events and the helm error *(to be decided)* ([Story 3.5][s3.5]) |
| `POST /v1/releases/{id}/dry-run`, `PATCH /v1/releases/{id}` | **Added.** Checks and runs an update of the version, the parameters, or both |

At this point it's unclear how and to what extent the `GET /v1/releases/{id}/status` route should be implemented. Should this actually look into multiple k8s objects and their state, or just print e.g. a health endpoint or the helm release's status?

**Changed.** Deploy and update share one sequence of checks with their dry-run. See [Share one check sequence between dry-run and the real call][h-checks].

### kaapana-system-admin

| Route | What it does |
|---|---|
| `GET /v1/applications` | **Added.** With `scope=platform`, it lists the applications that can be deployed platform-wide. |
| `GET /v1/releases` | **Added.** Lists the releases of all projects ([Story 3.4][s3.4]) |

**Changed.** The kaapana-system-admin uses every route of the application page in every project and platform-wide ([Story 5.1][s5.1]).

### Access-information-interface (AII)

**Added.** AII deploys one release of the application `project-namespace` for every project with `POST /v1/releases`, and undeploys it with `DELETE /v1/releases/{id}` when the project is deleted. It finds the release with `GET /v1/releases?application_id=project-namespace&name=project-<short_id>`. See [Charts that other services install](#charts-that-other-services-install-proposed).

### Workflows

**Added.** A workflow task deploys with a workflow origin in `POST /v1/releases`, and the user finishes with `POST /v1/releases/{id}/complete`. See [Interactive workflows](#interactive-workflows).

## Content of a helm-chart content

Extends [Content of a helm-chart content](MVP.md#content-of-a-helm-chart-content).

| Field | Meaning |
|---|---|
| `scopes` | **Added.** `project`, `platform`, or both. The default is `project` ([Q11][q11]). |
| `multi_deployable` | **Changed.** Whether the application can have several releases in the same scope. A scope is one project or the whole platform. The default is `false`. |

### The web interface of a release

Extends [The web interface of a release](MVP.md#the-web-interface-of-a-release).

**Added.** The web interface of a platform-wide release is found through the menu of the platform. See [Platform-wide releases](#platform-wide-releases).

### Changes to the schema *(proposed)*

**Added.** The model `HelmChartContent` in [api-mock-release-2/app/models.py][models] gets three fields:

- **`platform_secrets`.** A platform content declares the passwords that it needs. See [Privileged values for platform contents](#privileged-values-for-platform-contents).
- **`platform_value_mapping`.** It hands a platform value to a value of a public chart. See [Mapping platform values to `values.yaml`](#mapping-platform-values-to-valuesyaml).
- **`patches`.** They change the rendered chart. See [Adding annotations and advanced chart customization options](#adding-annotations-and-advanced-chart-customization-options).

## Configuration of parameters

Extends [Configuration of parameters](MVP.md#configuration-of-parameters).

### Rules

- **Added.** On an update, a parameter that exists in both versions keeps its value, a new parameter gets its default, and a dropped parameter disappears ([Stories 11.3][s11.3] and [11.4][s11.4]).
- **Changed** *(proposed)*. A secret parameter never becomes a chart value. The consumer keeps masking the value in its responses ([Story 3.2][s3.2]). This rule comes with Release 2 or with a release after it. See [Never return a secret, and keep it out of the helm values][h-secrets].

### Values that the Helm Chart Consumer sets *(proposed)*

Extends [Values that the Helm Chart Consumer sets](MVP.md#values-that-the-helm-chart-consumer-sets-proposed).

| Value | Meaning | Source |
|---|---|---|
| `scope` | **Added.** `project` or `platform` | [Q11][q11] |
| `project.id`, `project.short_id`, `project.namespace`, `project.bucket` | **Changed.** The project of the release. Only for the project scope. | [Story 2.5][s2.5], [Q6][q6] |
| `credentials_secret` | **Added.** The name of the secret with the credentials for Kaapana APIs. In a project, they belong to a technical user of the project. For the platform scope, [Q13][q13] decides on whose behalf the release acts. | [Story 4.5][s4.5], [Q7][q7], [Q13][q13] |
| The legacy `global` block | **Changed.** Removed. See [The legacy `global` block](#the-legacy-global-block). | |

#### The legacy `global` block

Extends [The legacy `global` block](MVP.md#the-legacy-global-block).

**Changed.** The consumer no longer passes the legacy block. It passes only the values under `global.kaapana`, and this list is fixed. kube-helm works differently: it copies the whole `global` block of the platform release into every chart ([utils.py][kh-utils]). [kaapanactl.sh][kaapanactl] writes passwords into that block, for example `global.credentials_keycloak_admin_password` and `global.smtp_password`, so every chart that gets the block can read them. The fixed list prevents this.

- **A legacy chart has to be converted.** See [Converting a legacy chart](#converting-a-legacy-chart).
- **Values that are missing in the list.** Legacy charts read many values of the block. Required values would need to be added to the values under `global.kaapana`. How this is handled is open.

#### Credentials of an application

Extends [Credentials of an application](MVP.md#credentials-of-an-application).

**Changed.** A release no longer gets the passwords of the platform. It gets `credentials_secret`, the name of a secret with a technical user of its project. An application then acts on behalf of its project and reaches only the data of this project ([Story 4.5][s4.5], [Q7][q7]).

- **The secret exists already.** The chart `project-namespace` creates the secret `project-user-credentials` in every project namespace, and workflow tasks use it today. See [Every project already has a namespace][h-namespace].
- **How an application uses it.** It reads the user name and the password from the secret, gets a token from Keycloak with the client secret, and calls a Kaapana API with the token. For MinIO, it exchanges the token for temporary keys. The library `kaapana_client` has both steps.
- **What changes for a chart.** A chart with the container `minio-sync` reads the user name and the password from the secret, and no longer from two values. The image `s3-mirror` gets the exchange of the token. All these charts share this image, so it changes once.
- **The client secret of Keycloak.** A chart that needs it reads the secret `oidc-client-secret` of its namespace. The chart `project-namespace` creates this secret in every project namespace, so the release has to run in the namespace of its project ([Q6][q6]).
- **All applications of a project share the technical user.** One application can reach everything that another application of the same project can reach.
- **The role of the technical user is open.** See [Open questions](#open-questions).

#### Privileged values for platform contents

**Added.** A platform content is a helm-chart content that belongs to the platform and not to an extension. See [Charts that other services install](#charts-that-other-services-install-proposed). Some of them need a password. The chart `project-namespace` builds the image pull secret and the OIDC client secret of a new project from `global.credentials_registry_password` and `global.oidc_client_secret`.

- **A platform content declares the privileged values that it needs**, in a field `platform_secrets` of `helm-chart-content.json`. The consumer passes exactly these values under `global.kaapana.secrets`, for example `registry_credentials` and `oidc_client_secret`.
- **A content of an extension never gets them.** A registration that comes from the Extension Manager and declares `platform_secrets` is rejected. The consumer decides this from the caller, and not from a field in the request.
- **The dry-run does not return them.** It shows a privileged value as set, like a secret parameter.
- **Helm stores them.** Helm keeps the values of a release in a secret in the namespace of the helm release. This is the same as today, and it is limited to the releases of platform contents. It is an exception to the rule that keeps a secret parameter out of the chart values. See [Rules](#rules).
- **`registry_credentials` holds the user name and the password of the registry.**
- **An alternative exists.** The chart `project-namespace` already copies two other passwords from the admin namespace with the helm function `lookup`, in `system_user_password.yaml` and `kaapana-service-password.yaml`. It could copy the registry secret and the OIDC client secret in the same way. Then no password passes through the values, and `platform_secrets` is not needed. The consumer needs the right to read secrets in the admin namespace in both cases, and `lookup` returns nothing in a client-side dry-run.

### How the chart values of a release are built

Extends [How the chart values of a release are built](MVP.md#how-the-chart-values-of-a-release-are-built).

**Added.** An update runs through the same flow as a deploy. The request is an update request, the validation runs at the update, and helm runs `helm upgrade`, first with a dry-run.

## Copies of an application

Extends [Copies of an application](MVP.md#copies-of-an-application).

### Listing, updating and uninstalling

Extends [Listing and uninstalling](MVP.md#listing-and-uninstalling).

- **Limits.** **Changed.** An application that is not multi-deployable has at most one release per project and at most one platform-wide release, counted over all its versions. A multi-deployable application can have several releases in a project, and several platform-wide ([Stories 8.1][s8.1] and [9.1][s9.1]).
- **Update.** **Added.** Every copy is updated on its own with `PATCH /v1/releases/{id}`. Registering a new version changes no running copy. A copy only shows `newer_version` ([Stories 11.1][s11.1] and [11.2][s11.2]).
- **Uninstalling the extension.** **Changed.** The version is deregistered and can no longer be deployed, unless another installed extension brings the same version. Its copies keep running, are marked with `version_registered: false`, and can still be opened, **reconfigured, updated to another version** and undeployed ([Story 1.2][s1.2], [Q4][q4]).

## Versioning

Extends [Versioning](MVP.md#versioning).

- **Changed.** A release runs exactly one version. Only an explicit update of that release changes it ([Story 11.2][s11.2]).
- **Added.** The order of the versions also decides `newer_version`, which a release shows when a newer version of its application is registered.

## Labels on the helm release *(proposed)*

**Added.** Helm knows two kinds of labels, and they serve different purposes: the labels on the objects of a chart, and the labels on the helm release.

**Labels on objects.** Helm adds the label `app.kubernetes.io/managed-by: Helm` and the annotations `meta.helm.sh/release-name` and `meta.helm.sh/release-namespace` to every object that it creates. It adds nothing else, and the consumer cannot add labels to objects without rewriting the rendered chart. The consumer therefore does not depend on object labels:

- Readiness and pods come from the manifest and from owner references. See [Derive the state, do not store it][h-state].
- The volume claims of a StatefulSet survive `helm uninstall`. Their names follow from the StatefulSet in the manifest, as `<claim template>-<StatefulSet>-<ordinal>`. See [Undeploying deletes the data, and helm does not do that alone][h-undeploy].
- A pod that needs a route through the network policies of its project sets the label itself, for example `network-access-opensearch`. See [Every project already has a namespace][h-namespace]. The labels that are allowed are documented for extension developers.

**Labels on the helm release.** `helm install --labels` stores labels with the release, and `helm list -l` filters by them. kube-helm does this already: it sets `kaapana.ai/<keyword>=True` for every keyword of a chart ([utils.py][kh-utils]). The consumer labels every helm release that it creates:

| Label | Value |
|---|---|
| `kaapana.ai/managed-by` | `helm-chart-consumer` |
| `kaapana.ai/release-id` | The id of the release |
| `kaapana.ai/application` | The application id |
| `kaapana.ai/scope` | `project` or `platform` |
| `kaapana.ai/project-id` | The id of the project, for the project scope |

The labels have two uses:

- [The reconciler](Release-later.md#the-reconciler) finds all helm releases of the consumer with one `helm list` and compares them with the records ([Story 12.3][s12.3]).
- An operator and the migration can tell three groups apart: releases of the consumer, legacy releases of kube-helm, and releases that `kaapanactl.sh` installs.

The record stays the source of truth. Anyone with access to the cluster can change a label, so the consumer never decides a permission by a label.

Releases that were deployed before Release 2 carry no labels. The consumer adds them on the next update of each release.

## Authorization

Extends [Authorization](MVP.md#authorization).

**Changed.** How callers inside the cluster prove who they are is open. The Extension Manager, workflow-api, AII and the installer all call from pod to pod, without a user. A network policy is no longer enough, because a platform content gets passwords and the right to deploy platform-wide only if the consumer knows its caller. See [Open questions](#open-questions).

**Added.** The table of the permission rules in [Option 1](MVP.md#option-1-check-by-role-to-be-decided) gets these rows:

| Action | Scientist of the project | PI of the project | kaapana-system-admin |
|---|---|---|---|
| Update in the project | no | yes | yes |
| Complete the work in a release that a workflow started | yes | yes | yes |
| Open the web interface of a platform-wide release | yes | yes | yes |
| List, details and status of platform-wide releases | no | no | yes |
| Deploy, update, undeploy platform-wide | no | no | yes |

### The origin of a release

Extends [The origin of a release](MVP.md#the-origin-of-a-release).

**Changed.** The origin records who or what deployed a release. The field is a union, like the placement. Its `type` tells the kinds apart. See `UserOrigin`, `WorkflowOrigin` and `ServiceOrigin` in [api-mock-release-2/app/models.py][models].

- **A user.** This is the default of a deploy request, as in the MVP.
- **A workflow task.** **Added.** The origin holds the workflow run, the task, and the user who started the run, if a user started it. Only workflow-api may send it. See [Put every permission rule in one table][h-permissions].
- **A service** *(proposed)*. **Added.** A platform service such as AII, the installer or the bootstrap job at platform deploy has no user. Its origin names the service. See [Charts that other services install](#charts-that-other-services-install-proposed).

### Platform-wide releases

**Added.** Only a kaapana-system-admin has access to a platform-wide release in the Helm Chart Consumer ([Story 9.4][s9.4]). What the release serves is open to users. An example is the SLIM viewer: every user can open it, but only an admin sees its release, its status and its configuration.

- **The API.** `GET /v1/releases` returns platform-wide releases only to an admin. For every other caller, the routes of a single platform-wide release answer 404.
- **The web interface.** The gateway lets users open it. The requests do not pass through the consumer.
- **How users find it.** The portal builds the menu of the platform from the ingresses of the cluster and their `kaapana.ai/ui.*` annotations ([menu.py][portal-menu]). A chart that wants a menu entry ships its own `Ingress` with these annotations and follows the guidelines of the portal. The charts of SLIM and Collabora do this today. This is a task of the chart and of the portal, and not of the consumer.

### Restricting who can open a release *(proposed)*

Extends [Who can open a release](MVP.md#who-can-open-a-release).

**Added.** The question is whether a release can be limited to a group, for example to principal investigators or to kaapana-system-admins.

- **Every user can open every platform-wide release** ([Story 9.2][s9.2]). This holds next to the rule of the MVP that every member of a project can open every release of the project.
- **The need is real for platform-wide releases.** An admin tool that is deployed platform-wide should not be open to every scientist.
- **Decide it together with Epic 9.** The restriction would be an optional field of a release that names the right a user needs to open it.
- **The gateway has to enforce it.** The requests to a web interface do not pass through the consumer. See [The gateway authenticates, the services authorize][h-gateway].
- **Admin-only needs no new rule.** A path without a rule in OPA is reachable only for admins, so this restriction can come first.

## Using a chart from a public registry *(proposed)*

Extends [Using a chart from a public registry](MVP.md#using-a-chart-from-a-public-registry-proposed).

### Mapping platform values to `values.yaml`

**Added.** The mapping hands a platform value to a value of the public chart.

**The problem.** Kaapana sets the platform values on every deploy, under `global.kaapana`. An example is `url_path`, the path under which the web interface is served. See [Values that the Helm Chart Consumer sets](MVP.md#values-that-the-helm-chart-consumer-sets-proposed). A public chart does not read `global.kaapana`. It expects such a value under a name of its own. JupyterHub, for example, expects the path in its value `hub.baseUrl`. The wrapper cannot connect the two. Its `values.yaml` is a static file that helm does not render, so it cannot refer to `global.kaapana.url_path`.

**The solution.** `helm-chart-content.json` lists which platform value goes into which chart value:

```json
{
  "platform_value_mapping": {
    "url_path": "jupyterhub.hub.baseUrl"
  }
}
```

At deploy and at update, the consumer writes the platform value of the release into the named chart value, in the values file of the release. For a release that is served under `/project/lung-ct/applications/anna-hub`, it sets `jupyterhub.hub.baseUrl` to this path. A public chart whose own values need a platform value can then be wrapped without changes.

- **The name of the field** *(to be decided)*. The example calls it `platform_value_mapping`.
- **The left side is a platform value.** Only the values of the table in [MVP.md](MVP.md#values-that-the-helm-chart-consumer-sets-proposed) can be mapped.
- **The right side is checked like a `chart_value`.** It must be a path that exists in `values.yaml`, and the consumer checks this at registration.
- **A user cannot set a mapped chart value.** It counts as a platform value, so no parameter may name it as its `chart_value`.

### Adding annotations and advanced chart customization options

Extends [The web interface of a wrapped chart](MVP.md#the-web-interface-of-a-wrapped-chart).

**Added.** A public chart often creates an `Ingress` from its values. The wrapper then sets the annotations in `chart/values.yaml` and maps `url_path` onto the path value of that `Ingress`. A public chart without an `Ingress` needs a template for it in the wrapper, as in the MVP.

A public chart does not offer a value for everything. Helm can hand the rendered manifest to a post-renderer before it installs it (`helm install --post-renderer`). The consumer uses this to apply patches that `helm-chart-content.json` declares. A patch names an object of the rendered chart and adds or overwrites a field of it. Any field can be patched. An example is an annotation on the `Ingress` of a public chart that has no value for annotations. Helm stores the patched manifest in the helm release, so `helm get manifest` and a rollback see the change.

A patch has a target and a list of operations. The target is the kind and the name of an object. Each operation has a path to a field of that object, and a value:

| Operation | What it does |
|---|---|
| `add` | Writes a field. It creates the field if the object does not have it, and it appends an entry if the path points to the end of a list. |
| `replace` | Overwrites a field that the object already has. The patch fails if the field is missing, so a change in the public chart does not go unnoticed. |

An example that adds an annotation to the `Ingress` of a public chart and overwrites the path that it serves:

```json
{
  "patches": [
    {
      "target": {"kind": "Ingress", "name": "<helm release name>-hub"},
      "operations": [
        {"op": "add", "path": "/metadata/annotations/kaapana.ai~1type", "value": "application"},
        {"op": "replace", "path": "/spec/rules/0/http/paths/0/path", "value": "<url_path>"}
      ]
    }
  ]
}
```

- **Format** *(to be decided)*. The example follows JSON Patch, which the patches of Kustomize use too. In a path of JSON Patch, `~1` stands for a slash inside a name. How a patch names the helm release name and a platform value is open, and the example writes them in angle brackets.
- **A patch can use platform values**, but not the parameters of a user. A parameter sets a chart value only, so the input of a user reaches the chart in one way.
- **A patch that matches no object is rejected at registration.** The consumer renders the chart for this check.
- **The mapping comes first.** A mapped platform value is set before helm renders the chart, so it can reach many templates at once. A patch changes one field of one object afterwards. It is for what the public chart offers no value for.

To check before the implementation:

- The post-renderer has to run on every upgrade as well. Otherwise the upgrade removes what the patches wrote.
- The target needs the kind and the name of the object, and the name often contains the helm release name. Patches of Kustomize already have a format for this.
- Helm 3 takes an executable as post-renderer, and Helm 4 takes a plugin.

## Charts that other services install *(proposed)*

**Added.** This section has no counterpart in [MVP.md](MVP.md), where kube-helm installs these charts.

### What exists

| Caller | What it does today |
|---|---|
| AII, when a project is created or deleted | Posts the chart `project-namespace` with the project's values to `/helm-install-chart` and `/helm-delete-chart` of kube-helm ([kubehelm.py][aii-kubehelm]) |
| base-installer, with the actions `copy` and `prefetch` | Posts every image to `/pull-docker-image` of kube-helm ([run.py][base-installer]). kube-helm installs one release of `pull-docker-chart` per image. |
| kube-helm, in an init job | Renders every chart in its cache with a dry-run, collects the images, and pulls them ([prefetch_extensions.py][kh-prefetch]) |

### Decision

These charts are helm-chart contents. Each one has a `helm-chart-content.json` with declared parameters, and its releases are deployed, updated and undeployed with the same routes as every other release. There are no separate routes, and no caller passes raw values.

The differences to other helm-chart contents all follow from one point: they belong to the platform and not to an extension, so the Extension Manager is not involved. This document calls them platform contents. The [glossary][glossary] of the concept defines a helm-chart content as a content type of an extension, and this decision widens that definition.

AII no longer needs its client for kube-helm ([kubehelm.py][aii-kubehelm]):

| Caller | When | Call |
|---|---|---|
| AII | A project is created | `POST /v1/releases` with the application `project-namespace`, the name `project-<short_id>`, the platform placement, and the project as parameters |
| AII | A project is deleted | `DELETE /v1/releases/{id}`, after the check that the project has no releases ([Q9][q9]) |
| AII | The platform was upgraded | `PATCH /v1/releases/{id}` with the new version, for the release of every project |
| base-installer | For every image | `POST /v1/releases` with the application `pull-docker-chart`, a generated name, and the image as parameters |

AII finds the release of a project with `GET /v1/releases?application_id=project-namespace&name=project-<short_id>`. A parameter for the name of the project can be added later, and a rename is then a `PATCH`.

### The content of `project-namespace`

```json
{
  "name": "project-namespace",
  "display_name": "Project namespace",
  "description": "Creates the namespace of a project and what the project needs in it.",
  "scopes": ["platform"],
  "multi_deployable": true,
  "parameters": [
    {"key": "project_id", "label": "Project id", "type": "string", "required": true, "chart_value": "global.project_id"},
    {"key": "project_short_id", "label": "Short id", "type": "string", "required": true, "chart_value": "global.project_short_id"},
    {"key": "project_namespace", "label": "Namespace", "type": "string", "required": true, "chart_value": "global.project_namespace"}
  ],
  "platform_secrets": ["registry_credentials", "oidc_client_secret"]
}
```

AII passes these values to kube-helm as `extension_params` today, together with `namespace`, which the chart does not read. The chart has to list them in its `values.yaml`, and it has to read the platform values under `global.kaapana`, like every converted legacy chart. See [Converting a legacy chart](#converting-a-legacy-chart). It also reads `global.dev_files`, which is not a platform value yet. The content of `pull-docker-chart` declares the parameters `registry_url`, `image` and `version`, and no `platform_secrets`. The registry is a parameter because the base-installer sends one per image.

### How a platform content differs

| | Content of an extension | Platform content |
|---|---|---|
| Registered by | The Extension Manager, when the extension is installed | The bootstrap job at platform deploy, or the service that deploys it *(to be decided)* |
| Scopes | Project, platform or both | Platform only |
| Deployed by | Users through the gateway, workflow-api, or the bootstrap job | A platform service, from inside the cluster |
| Origin of its releases | A user, a workflow task, or the bootstrap job as a service | A service |
| Shown on the application page | Yes | Only when a kaapana-system-admin filters for it |
| Platform values | `global.kaapana` | `global.kaapana`, and the privileged values that it declares |

- **The release of a project is platform-wide.** Its placement cannot be the project. The namespace of the project does not exist before the release is deployed. A release in the project would also block the deletion of its own project, because AII refuses the deletion while the project has releases. The project is therefore passed as parameters, and the consumer does not ask AII about it.
- **Users do not see these releases.** Only a kaapana-system-admin sees a platform-wide release ([Story 9.4][s9.4]). See [Platform-wide releases](#platform-wide-releases). No third scope is needed.
- **A kaapana-system-admin always has access.** An admin can update and undeploy these releases like every other release. Undeploying the release of a project removes what the chart created for the project, such as its secrets, its network policies and its runtime deployment. The namespace itself stays, because its template sets `helm.sh/resource-policy: keep`.
- **The application page hides them by default.** It leaves out the releases of platform contents unless the admin filters for them. This is a rule of the UI. The API returns these releases to an admin like every other release.
- **The services need the right to deploy platform-wide.** Only kaapana-system-admins have it today. AII and the installer get it together with their identity as a service.
- **`multi_deployable` covers one release per project.** Since the field holds for both scopes, a platform content with `multi_deployable: true` can have many platform-wide releases. No exception from the limit is needed.
- **Registration.** The registration of `project-namespace` must be done before AII creates its first project. The version is the build version. Where the chart comes from depends on the open question of how a chart reaches the consumer.
- **Who registers a platform content** *(to be decided)*. A platform content belongs to no extension, so the Extension Manager does not register it, and a service can only deploy a chart that is registered. Two options exist:
  - **A bootstrap job at platform deploy registers all platform contents.** One place holds all charts of the platform, as kube-helm does today, and only the job needs the right to register a platform content. The job must have run before AII creates its first project, and it has to run again after a platform upgrade.
  - **The service that deploys a platform content registers it**, when the service starts. Registering twice changes nothing, so no start order is needed, and a restart after an upgrade registers the new version. Every such service then has to carry the files of its chart, which AII does not do today, and every such service needs the right to register a platform content.
- **Removing the releases of image pulls** *(to be decided)*. kube-helm installs `pull-docker-chart`, waits, and deletes the release ten seconds later. In the new system the installer deletes each release when it is ready, or a content can declare that its release is removed when its job has finished.

The dry-run of all charts in the init job is not replaced. The consumer is not responsible for making images available ([Q10][q10]).

Reasons and costs:

- **Why one kind of release.** One API and one format cover every chart. A chart of the platform follows the same rules as a chart of an extension, so there is no second path that could skip a check.
- **Why not in the other services.** The ticket wants to remove the legacy system in 0.8.0. If AII and the installer ran helm themselves, three services would carry helm code and rights on the whole cluster.
- **Cost: rights.** The service account of the consumer needs rights on the whole cluster. The chart `project-namespace` creates a namespace, and it creates secrets and network policies in that namespace, which is not the namespace of the helm release. It also reads two secrets in the admin namespace.
- **Cost: identity.** A platform content gets passwords, a service origin and the right to deploy platform-wide only if the consumer knows its caller. This makes the open question about callers inside the cluster a blocker for removing kube-helm.
- **Cost: start order.** The consumer has to run before AII creates a project. Where the consumer runs is open.

## Charts at platform deploy and charts from the legacy page *(proposed)*

**Added.** This section has no counterpart in [MVP.md](MVP.md), where kube-helm installs these charts. [Converting a legacy chart](MVP.md#converting-a-legacy-chart) is part of the MVP.

### What exists

[deployment_config.yaml][deployment-config] of `kaapana-admin-chart` lists `preinstall_extensions`: `kaapana-platform-chart`, `code-server-chart` and `kaapana-workflows-core`. The build writes the list with versions into the values of `kaapana-admin-chart`. At deploy, an init job of kube-helm installs each entry from its chart cache ([preinstall_extensions.py][kh-preinstall]).

### The three kinds of preinstalled charts

| Kind | Example | In the new system |
|---|---|---|
| The platform itself | `kaapana-platform-chart` | A platform content, or `kaapanactl.sh` installs it directly. The consumer cannot install the chart that it is part of. Where the consumer runs is open. |
| An application | `code-server-chart` | An extension with a helm-chart content. It is registered through the Extension Manager and then deployed through the consumer. |
| Workflows | `kaapana-workflows-core` | An extension with workflow contents. The Helm Chart Consumer is not involved. |

### What the bootstrap needs

Registering makes an application available but deploys nothing, and a new application is disabled in every project ([Q8][q8]). An entry in `preinstall_extensions` therefore has to say more than a name:

```yaml
preinstall_extensions:
- name: code-server
  version: 0.8.0
  releases:
  - name: code-server
    placement:
      scope: platform
    parameters: {}
```

A job at platform deploy processes the list. It installs each extension through the Extension Manager, and then deploys the listed releases through the consumer. The same job can register the platform contents, which have no extension. See [How a platform content differs](#how-a-platform-content-differs).

- The job must be safe to repeat. Registering is repeatable already. For a release, the job first asks `GET /v1/releases?name=<name>` and deploys only if the release is missing.
- The job calls from inside the cluster, so it needs the same answer about its identity as the other callers.

### Charts that were installed before 0.8.0

Releases that kube-helm created have no record in the consumer. They carry the labels `kaapana.ai/<keyword>=True`.

- **The consumer does not adopt them.** `GET /v1/releases` lists only releases that the consumer created. See [Keep a record of every release][h-records]. A legacy chart has no `helm-chart-content.json`, so the consumer would not know its parameters.
- **The upgrade to 0.8.0 handles them.** The migration lists the legacy releases by their labels and reports them. The admin undeploys them before the upgrade, or keeps kube-helm for one more release to remove them later.
- **Not every volume survives.** The volume templates of `kaapana-library-chart` set `helm.sh/resource-policy: keep` for project volumes, and for the other volumes of a chart only if the chart is not multi-installable. Uninstalling a multi-installable legacy release therefore deletes those volumes.

There could be solutions that keep the data of a legacy release. These two are possible ideas:

- **Idea: adopt the release.** The legacy chart is converted and registered. The consumer then takes over the existing helm release with `helm upgrade` under its old name, after it has checked that the converted chart renders the same objects. Helm allows this, because only the name and the namespace of a helm release are fixed. This may be a lot of effort, and an object that the converted chart renames would lose its data.
- **Idea: keep only the volume.** The admin marks the volume claim of the legacy release so that `helm uninstall` keeps it. A new release of the converted chart then uses this claim and does not create one. This is less effort, but the chart has to support an existing claim.

## Converting a legacy chart

Extends [Converting a legacy chart](MVP.md#converting-a-legacy-chart).

**Added.** The legacy `global` block is gone, so a chart also has to change how it reads the values of the platform:

| Legacy | New |
|---|---|
| `global.*` copied from the platform release, for example `global.registry_url` | The platform values under `global.kaapana` |
| `global.project_id`, `global.project_short_id`, `global.project_namespace` | `global.kaapana.project.id`, `global.kaapana.project.short_id`, `global.kaapana.project.namespace` |
| `global.credentials_minio_username`, `global.credentials_minio_password` | The technical user in the secret that `credentials_secret` names. See [Credentials of an application](#credentials-of-an-application). |
| `global.oidc_client_secret` | The secret `oidc-client-secret` of the namespace |

## Interactive workflows

**Added.** Epic 7, a workflow that starts an application and waits for the user, has the priority Release 2 in [concept.md][e7]. Release 2 therefore adds the workflow origin, `POST /v1/releases/{id}/complete` and the filters `origin_type` and `workflow_run_id`. [api-mock-release-2/](api-mock-release-2/) holds them as a proposal. [Q15][q15] and the question in [Keep the outcome of a workflow step after its release is gone][h-workflow-outcome] have to be answered for this.

This priority conflicts with the goal of the ticket to remove the legacy system in 0.8.0. kube-helm serves these applications today with `/complete-active-application`, `/active-applications` and `/pending-applications-count`. See [An older helm deployer exists][h-kube-helm]. Until Epic 7 is implemented, either kube-helm stays for these routes, or 0.8.0 has no interactive workflow steps.

## Open questions

Extends [Open questions](MVP.md#open-questions).

| Question | What depends on it |
|---|---|
| [Q12][q12]: An application is enabled per project. When a new version of an enabled application is registered, can it be deployed at once, or does an admin have to enable it first? | **Added.** The bootstrap job. It deploys a release right after it has registered the version, so it depends on whether the version can be deployed at once. |
| [Q13][q13]: An application in a project acts on behalf of its project. On whose behalf does a platform-wide application act when a user opens it in the context of a project? | **Added.** Which credentials a platform-wide release gets, that is, which secret `credentials_secret` names for the platform scope. |
| The Extension Manager and AII call the consumer from pod to pod, without a user and without the gateway. How does the consumer know that such a call really comes from them? In Release 2, workflow-api, the base-installer and the bootstrap job call in the same way. | **Changed.** More depends on it. A platform content gets passwords, a service origin and the right to deploy platform-wide only if the consumer knows its caller, so a network policy is no longer enough. See [Authorization](#authorization). |
| Which role does the technical user get whose credentials an application uses for Kaapana APIs? [Q7][q7] says the rights of a scientist, but the existing technical user of a project is created as a principal investigator ([create_project_user.py][create-project-user]). | **Added.** Whether `credentials_secret` can name the existing secret `project-user-credentials`, or whether a project needs a second technical user. |
| Legacy charts read many values of the legacy `global` block. Which of them are added to the values under `global.kaapana`? | **Added.** What a converted chart can still read when the block is no longer passed. |
| Helm creates the objects of a chart with the rights of the service account of the consumer. Which rights does this account get? | **Changed.** Also whether `project-namespace` can be deployed. This chart creates a namespace, and secrets and network policies in it, so it needs rights on the whole cluster. |
| How do the files of a chart reach the consumer at registration? | **Changed.** Also the registration of a platform content, which does not come from the Extension Manager. |
| Is the consumer a part of `kaapana-admin-chart`, which `kaapanactl.sh` installs, or of `kaapana-platform-chart`, which is installed after it? | **Changed.** Also who installs `kaapana-platform-chart`. The consumer cannot install the chart that it is a part of. |
| A platform content belongs to no extension. Who registers it: a bootstrap job at platform deploy, or the service that deploys it? | **Added.** The start order of the services, and which service has to carry the chart files of a platform content. See [How a platform content differs](#how-a-platform-content-differs). |
| Does kube-helm stay in 0.8.0 until the consumer covers interactive workflow steps and legacy releases? | **Added.** Whether the legacy system can be removed in 0.8.0, as the ticket wants. See [Scope](#scope). |
| What does `GET /v1/releases/{id}/status` return: the state of every Kubernetes object of a release, or only a summary such as the status of the helm release? | **Added.** The details that the application page can show for a release, and how much the consumer has to read from the cluster. |

[glossary]: concept.md#glossary
[e7]: concept.md#epic-7-interactive-steps-in-workflows
[s1.2]: concept.md#story-12-deregistering-a-helm-chart-content-when-its-extension-is-uninstalled
[s2.5]: concept.md#story-25-working-on-existing-data
[s3.2]: concept.md#story-32-seeing-the-configuration-of-a-deployed-application
[s3.4]: concept.md#story-34-overview-of-all-deployed-applications
[s3.5]: concept.md#story-35-seeing-the-details-of-a-deployed-application
[s4.5]: concept.md#story-45-authenticated-access-to-kaapana-apis
[s5.1]: concept.md#story-51-default-permissions
[s8.1]: concept.md#story-81-deploying-an-application-multiple-times
[s9.1]: concept.md#story-91-deploying-an-application-platform-wide
[s9.2]: concept.md#story-92-using-a-platform-wide-application
[s9.4]: concept.md#story-94-platform-wide-deployed-applications-are-managed-only-by-kaapana-system-admins
[s11.1]: concept.md#story-111-browsing-available-versions
[s11.2]: concept.md#story-112-updating-a-deployed-application-to-a-new-version
[s11.3]: concept.md#story-113-updating-deploy-parameters
[s11.4]: concept.md#story-114-setting-deploy-parameters-when-updating-the-version
[s12.3]: concept.md#story-123-detecting-changes-made-outside-the-helm-chart-consumer
[q4]: QandA.md#q4-deregistered-content
[q6]: QandA.md#q6-namespaces
[q7]: QandA.md#q7-identity-of-api-credentials
[q8]: QandA.md#q8-default-enablement
[q9]: QandA.md#q9-project-deletion
[q10]: QandA.md#q10-offline-installations
[q11]: QandA.md#q11-scope
[q12]: QandA.md#q12-enabling-new-versions
[q13]: QandA.md#q13-identity-of-platform-wide-applications
[q15]: QandA.md#q15-deploying-from-workflows
[h-gateway]: handoff.md#the-gateway-authenticates-the-services-authorize
[h-kube-helm]: handoff.md#an-older-helm-deployer-exists
[h-state]: handoff.md#derive-the-state-do-not-store-it
[h-undeploy]: handoff.md#undeploying-deletes-the-data-and-helm-does-not-do-that-alone
[h-namespace]: handoff.md#every-project-already-has-a-namespace
[h-records]: handoff.md#keep-a-record-of-every-release
[h-permissions]: handoff.md#put-every-permission-rule-in-one-table
[h-checks]: handoff.md#share-one-check-sequence-between-dry-run-and-the-real-call
[h-secrets]: handoff.md#never-return-a-secret-and-keep-it-out-of-the-helm-values
[h-workflow-outcome]: handoff.md#keep-the-outcome-of-a-workflow-step-after-its-release-is-gone
[models]: api-mock-release-2/app/models.py
[create-project-user]: ../../data-separation/project-namespace/docker/files/create_project_user.py
[kh-utils]: ../../kaapana-admin/kube-helm/docker/files/backend/app/utils.py
[kaapanactl]: ../../../kaapanactl.sh
[kh-prefetch]: ../../kaapana-admin/kube-helm/docker/files/backend/scripts/prefetch_extensions.py
[kh-preinstall]: ../../kaapana-admin/kube-helm/docker/files/backend/scripts/preinstall_extensions.py
[portal-menu]: ../portal-api/docker/app/menu.py
[aii-kubehelm]: ../../data-separation/access-information-interface/docker/backend/files/app/projects/kubehelm.py
[base-installer]: ../../utils/base-installer/files/run.py
[deployment-config]: ../../../platforms/kaapana-admin-chart/deployment_config.yaml
