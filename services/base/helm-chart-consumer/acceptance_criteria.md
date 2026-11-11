# Helm Chart Consumer: answers to the acceptance criteria

This document answers the acceptance criteria of the concept ticket. Every answer has one part for the MVP and one part for Release 2. The answers are short, and each one links to the section that holds the details:

- [MVP.md](MVP.md) holds the decisions for the MVP.
- [Release-2.md](Release-2.md) holds what Release 2 adds.
- [Release-later.md](Release-later.md) holds what comes after Release 2.

The ticket and the concept use different words. "Install a chart" in the ticket is "deploy an application" in the concept, and the result is a release. See [Words of the ticket and words of the concept](MVP.md#words-of-the-ticket-and-words-of-the-concept).

## Acceptance criteria (ticket)

The questions and the checklist are quoted from the ticket.

### 1. How does the interface of a new service with following functionalities look like: chart install with values, update, uninstall, status (starting, running, failed, with a reason)

**MVP.** Install, uninstall and status have a route. A release is one installed chart.

| The ticket asks for | Route | What it does |
|---|---|---|
| Install with values | `POST /v1/releases` | Deploys an application with parameter values. `POST /v1/releases/dry-run` runs the same checks before, without deploying. |
| Uninstall | `DELETE /v1/releases/{id}` | Undeploys the release and deletes its volumes |
| Status | `GET /v1/releases/{id}` | Returns the release with its `state`, which is `deploying`, `ready` or `failed`, and with the reason in `state_reason` |

See [Interface of the service](MVP.md#interface-of-the-service) for all routes, grouped by caller.

**Release 2.** The update and the details of the status are added.

| The ticket asks for | Route | What it does |
|---|---|---|
| Update | `PATCH /v1/releases/{id}` | Changes the version of a release, its parameters, or both. `POST /v1/releases/{id}/dry-run` runs the same checks before, without changing anything. |
| Status, in detail | `GET /v1/releases/{id}/status` | Returns the Kubernetes objects, the pods, the events and the helm error of a release. How much of this the route returns is still to be decided. |

See [Interface of the service](Release-2.md#interface-of-the-service).

### 2. What a `helm-chart` content contains

**MVP.** A helm-chart content is one directory in an extension. It holds two things:

- **`chart/`** is a plain helm chart.
- **`helm-chart-content.json`** is what Kaapana reads. It has these fields:

| Field | Meaning |
|---|---|
| `name` | The id of the application |
| `display_name`, `description` | What users see |
| `multi_deployable` | Whether a project can have several releases of the application |
| `parameters` | The values that a user may set at deploy. Each parameter has a key, a label, a type, rules, and the path of the chart value that it sets. |

The file does not declare a web interface. The chart creates an `Ingress` for it and marks it with an annotation, and the consumer finds it there. `extension_manifest.json` declares the content with the `contentType` `helm-chart-v1` *(proposed)*. See [Content of a helm-chart content](MVP.md#content-of-a-helm-chart-content).

**Release 2.** `helm-chart-content.json` gets two more fields:

| Field | Meaning |
|---|---|
| `scopes` | Where the application can be deployed: in a project, platform-wide, or both. The default is a project. |
| `platform_secrets` *(proposed)* | The passwords of the platform that the chart needs, such as the registry credentials. Only a chart of the platform itself may declare it. |

See [Content of a helm-chart content](Release-2.md#content-of-a-helm-chart-content) and [Privileged values for platform contents](Release-2.md#privileged-values-for-platform-contents).

### 3. How can an existing chart from a public registry be used with least amount of effort

**MVP.** The public chart is not changed. The extension wraps it in a small chart of its own:

- `chart/Chart.yaml` lists the public chart as a dependency. The build packs it into the extension, so the consumer needs no access to the public registry.
- `chart/values.yaml` sets the values of the public chart.
- `helm-chart-content.json` declares the name, the description and the parameters.
- A template of the wrapper creates the `Ingress` of the web interface.

One limit exists: helm cannot pass a value of the platform, such as the URL path, into a value of the public chart. A public chart that needs such a value cannot be wrapped without a change. See [Using a chart from a public registry](MVP.md#using-a-chart-from-a-public-registry-proposed).

**Release 2.** Two additions remove the limit:

- **A mapping.** `helm-chart-content.json` maps a value of the platform onto a value of the public chart, for example the URL path onto `jupyterhub.hub.baseUrl`. See [Mapping platform values to `values.yaml`](Release-2.md#mapping-platform-values-to-valuesyaml).
- **Patches.** `helm-chart-content.json` declares patches that add or overwrite any field of an object of the public chart. The consumer applies them after helm has rendered the chart, with a helm post-renderer. An example is an annotation on the `Ingress` of a public chart that has no value for annotations. See [Adding annotations and advanced chart customization options](Release-2.md#adding-annotations-and-advanced-chart-customization-options).

### 4. How is the old multiinstallable concept defined with this content type, i.e. how can several copies run? How copies are listed, what an update does to running copies, what uninstall does while copies run etc

**MVP.** `multi_deployable: true` in `helm-chart-content.json` replaces the keyword `kaapanamultiinstallable`. Every copy is a release with its own id, helm release name, URL and parameters.

| Question of the ticket | Answer |
|---|---|
| How can several copies run? | The consumer gives every release its own helm release name, for example `jupyterlab-3f2a9c1e`. An application that is not multi-deployable has at most one release per project. |
| How are copies listed? | `GET /v1/releases?application_id=<id>&project_id=<id>` |
| What does an update of the extension do to running copies? | Nothing. The new version is registered, and the running copies keep their version. |
| What does uninstalling the extension do while copies run? | The version can no longer be deployed. Its copies keep running and can still be opened and undeployed. |
| How is one copy removed? | `DELETE /v1/releases/{id}` undeploys it and deletes its volumes. |

See [Copies of an application](MVP.md#copies-of-an-application).

**Release 2.** A copy can be updated, and copies can run platform-wide.

| Question of the ticket | Answer |
|---|---|
| What does an update do to running copies? | Every copy is updated on its own with `PATCH /v1/releases/{id}`. A copy shows in `newer_version` that a newer version is registered. |
| What does uninstalling the extension do while copies run? | The version can no longer be deployed. Its copies keep running and can still be opened, **reconfigured, updated to another version** and undeployed. |
| How can several copies run? | The limit also holds platform-wide: one platform-wide release, or several if the application is multi-deployable. |

See [Copies of an application](Release-2.md#copies-of-an-application).

### 5. Charts installed by other services with values (e.g. AII's project namespace or the image prefetch from installer) how do they interact with extension manager / Helm API?

**MVP.** Nothing changes for these charts. They do not interact with the Extension Manager or with the Helm Chart Consumer:

- AII keeps posting the chart `project-namespace` to kube-helm when a project is created or deleted.
- The base-installer keeps posting every image to kube-helm, which installs the chart `pull-docker-chart`.

AII calls the consumer for one thing only: before it deletes a project, it asks `GET /v1/releases?project_id=<id>` and refuses the deletion while releases exist. See [Scope](MVP.md#scope) and [Interface of the service](MVP.md#interface-of-the-service).

**Release 2.** These charts become helm-chart contents of the platform. Each one has a `helm-chart-content.json` with declared parameters, and its releases use the same routes as every other release. They still do not interact with the Extension Manager, because they belong to no extension.

| Caller | When | Call to the Helm Chart Consumer |
|---|---|---|
| AII | A project is created | `POST /v1/releases` with the application `project-namespace` and the project as parameters |
| AII | A project is deleted | `DELETE /v1/releases/{id}` |
| AII | The platform was upgraded | `PATCH /v1/releases/{id}` with the new version |
| base-installer | For every image | `POST /v1/releases` with the application `pull-docker-chart` and the image as parameters |

AII no longer needs its client for kube-helm. This requires that the consumer knows which service calls it, that it has rights on the whole cluster, and that it can pass passwords of the platform to these charts. See [Charts that other services install](Release-2.md#charts-that-other-services-install-proposed).

**Open question: who registers these charts.** They belong to no extension, so the Extension Manager does not register them, and other services, like AII for `project-namespace`, can only deploy a chart that is registered. Two options exist:

- **A bootstrap job at platform deploy registers all of them.** One place holds the charts, and only the job needs the right to register them. The job must have run before AII creates its first project.
- **Each service registers the chart that it deploys**, when the service starts. No start order is needed. Every such service then has to carry the files of its chart, which AII does not do today.

See [How a platform content differs](Release-2.md#how-a-platform-content-differs).

### 6. How does the UI get the install parameters form (i.e. `extension_params` in chart annotations in the legacy code)?

**MVP.** The form belongs to deploying an application, and not to installing an extension. The Extension Manager therefore needs no form.

1. The UI reads the parameter declarations from `GET /v1/applications/{id}/versions/{version}`, in `content.parameters`.
2. It builds the form from them. Each declaration has a label, a type, rules and a default.
3. It checks the input with `POST /v1/releases/dry-run`, and deploys with `POST /v1/releases`.

See [Configuration of parameters](MVP.md#configuration-of-parameters).

In the legacy code, `extension_params` is a block in the `values.yaml` of a chart, for example in [the chart of JupyterLab][jupyterlab-values], and not a chart annotation. kube-helm reads the block with `helm show values`. [Converting a legacy chart](MVP.md#converting-a-legacy-chart) shows how such a block becomes parameter declarations.

**Release 2.** The same form is used for an update. The UI fills it with the current values from `GET /v1/releases/{id}` and checks the input with `POST /v1/releases/{id}/dry-run`. See [Configuration of parameters](Release-2.md#configuration-of-parameters).

### 7. What is required to handle the new `deployment_config` Helm charts that exist on platform charts at deploy time? And other charts that are installed through the legacy page before 0.8.0.

**MVP.** Nothing is required, because kube-helm keeps both tasks:

- An init job of kube-helm keeps installing the `preinstall_extensions` of `deployment_config.yaml` at platform deploy.
- The releases that were installed from the legacy page stay with kube-helm.

A legacy chart that should be deployed through the consumer has to be converted. See [Scope](MVP.md#scope) and [Converting a legacy chart](MVP.md#converting-a-legacy-chart).

**Release 2.** Three things are required:

- **A bootstrap job at platform deploy.** It installs each listed extension through the Extension Manager and then deploys its releases through the consumer. Whether it also registers the charts that other services install, such as `project-namespace` for AII, is an open question. See [answer 5](#5-charts-installed-by-other-services-with-values-eg-aiis-project-namespace-or-the-image-prefetch-from-installer-how-do-they-interact-with-extension-manager-helm-api) and [How a platform content differs](Release-2.md#how-a-platform-content-differs).
- **An extended format of `preinstall_extensions`.** Registering deploys nothing, so every entry also lists the releases to deploy, with their placement and parameters.
- **A decision about who installs the platform chart.** The consumer cannot install the chart that it is part of.

See [Charts at platform deploy and charts from the legacy page](Release-2.md#charts-at-platform-deploy-and-charts-from-the-legacy-page-proposed).

Legacy releases are not adopted, because they have no `helm-chart-content.json`. The upgrade to 0.8.0 lists and reports them. The admin undeploys them before the upgrade, or keeps kube-helm for one more release. There could be solutions that keep a legacy release or its data, such as adopting the release or keeping only its volume. See [Charts that were installed before 0.8.0](Release-2.md#charts-that-were-installed-before-080).

### Checklist

- [ ] A written proposal answering the above questions
- [ ] Proposal should contain API sketches that show all entry points to the service: the consumer operations used by the Extension Manager (install, update, uninstall, status of a content), and API used by the app page, AII and the installer (that is the current list, can be more)
- [ ] Reviewed with the leads and presented to developers
- [ ] Downstream issues are drafted

State of the checklist:

- **Written proposal.** [MVP.md](MVP.md), [Release-2.md](Release-2.md) and [Release-later.md](Release-later.md), with [concept.md](concept.md) and [handoff.md](handoff.md).
- **API sketches.** [api-mock/](api-mock/) covers the Extension Manager, the application page, the admin and the deletion check of AII. It does not show platform contents yet: the registration requires an extension, and there is no service origin.
- **Review.** Not done.
- **Downstream issues.** Not drafted. [A possible order for the MVP][h-mvp-order] is a starting point.

[h-mvp-order]: handoff.md#a-possible-order-for-the-mvp
[jupyterlab-values]: ../../applications/jupyterlab/jupyterlab-chart/values.yaml
