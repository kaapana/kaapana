# Handoff: from the concept to an implementation of the Helm Chart Consumer

This document is for the people who implement the Helm Chart Consumer. It collects what the concept work found
out about the code that the consumer has to fit into, and what the decisions in [concept.md](concept.md) and
[QandA.md](QandA.md) mean for the code. Paths are relative to the repository root.

## What exists

| Artifact | Content |
|---|---|
| `services/base/helm-chart-consumer/concept.md` | Epics and user stories with priorities. Details marked *(proposed)* still need confirmation. |
| `services/base/helm-chart-consumer/QandA.md` | Answers to Q1 to Q11. Q6 and Q12 to Q15 are open. |
| `services/base/helm-chart-consumer/docker/` | Click-through UI mock with seed data and no backend |
| `services/base/helm-chart-consumer/api-mock/` | API proposal: FastAPI routes with docstrings, pydantic models and fixed example responses |

The API mock and the UI mock are independent. The UI mock does not call the API mock. The examples of the API
mock reuse part of the seed data of the UI mock, with fewer applications and parameters.

## Facts about the code the consumer plugs into

### The Extension Manager calls consumers as Python plugins

The Extension Manager has no HTTP contract for content consumers. It runs one Python class per content type
inside its own process:

- `ContentInstaller` with `can_install`, `install` and `uninstall`, and `InstallationResult(success, message,
  location)` are in `services/base/extension-manager-service/docker/files/app/v1/services/dispatch/content.py`.
- The installers are listed by hand in `.../dispatch/__init__.py`: `Dispatcher(installers=[WorkflowInstaller()])`.
  A `HelmChartInstaller` has to be added there.
- `.../dispatch/consumers/workflows.py` is the template. It reads the content files from the Extension Manager's
  disk, posts them to `http://workflow-api.services.svc:80/v1/workflows`, and stores the `Location` response
  header as the content's location. It uninstalls with `DELETE {base}{location}`, where the base ends in `/v1`.

This has consequences for the consumer API:

- The workflow installer needs a `Location` relative to `/v1`, as in `/applications/jupyterlab/versions/4.3.0`,
  because it appends the location to a base that ends in `/v1`. A `HelmChartInstaller` is new code and could build
  its URLs differently. The API mock still follows this rule for every `Location` header, so that both installers
  can work the same way.
- Uninstalling passes only `name`, `content_type` and `location`, not the version. The location must therefore
  identify the version.
- If `install` returns no location, a later uninstall is skipped without an error, and the content still shows as
  uninstalled.
- A retry of a failed installation posts the same content again. Registering must therefore be idempotent. The API
  mock uses `PUT` on the version for this reason.
- The calls go from pod to pod and bypass the gateway. They carry no user identity and no `Project` header, and
  Kaapana has no service identity that the Extension Manager could present instead. The consumer therefore cannot
  tell the Extension Manager from any other pod that reaches it. The registration routes must only be reachable
  from inside the cluster, and network policies have to limit which pods reach them. Through the gateway, the
  realm role `admin` is allowed every path, so the consumer or an OPA rule has to refuse these routes there.
- `InstalledContent` has no field for a failure reason. The background job drops `result.message` and only logs
  exceptions. Showing the reason of `INSTALLATION_FAILED` in the Extension Manager (Story 1.1) needs a change in
  the Extension Manager.
- `Dispatcher.find_installer` raises `RuntimeError` for an unknown content type. The install route expects it
  to return nothing in that case, so its 400 branch never runs and the request answers 500.
- The Extension Manager has no update path, neither in its routes nor in `ContentInstaller`. Story 1.3 needs one,
  or it stays "install the new version, then uninstall the old one".
- The contents of an extension are installed one after the other, and nothing is rolled back. If a later content
  fails, a helm-chart content that was installed before stays registered, although the extension shows as failed.
- The uninstall route asks no consumer before it starts. Story 1.2 wants the admin to see the affected deployed
  applications first, which `GET /v1/deployments?application_id=<id>&version=<version>` answers. The Extension
  Manager needs a change to show them.
- The `contentType` name for helm-chart contents is not defined yet. `concept.md` suggests `helm-chart-v1`.
- How the packaged chart reaches the consumer is not decided. The workflow installer sends JSON. A chart needs a
  file upload, an archive in the body, or a reference to the extension's OCI artifact. The API mock uses
  `chart_reference` as a placeholder. The Extension Manager deletes the pulled extension from its disk when the
  installation ends, so the chart has to reach the consumer during the install call.

### The gateway authenticates, the services authorize

Most Kaapana services do not verify the token themselves. dicom-web-filter is an exception and checks the token
signature. oauth2-proxy, Traefik forwardAuth, auth-backend and OPA sit in front of every service and pass trusted
headers:

- `X-Forwarded-User` holds the user id. `X-Forwarded-Access-Token` holds the Keycloak token, whose claims carry
  the realm roles (`admin`, `project-manager`, `user`) and the project rights.
- `Project` holds the JSON record of the project from the access-information-interface (AII), with `id`,
  `short_id`, `kubernetes_namespace`, `s3_bucket` and `multiinstallable_whitelist`. auth-backend sets it only for
  URLs under `/project/<id>/` (`services/kaapana-admin/auth-backend/docker/files/main.py`), and refuses
  non-members there.
- The project roles `scientist` and `principal-investigator` and their rights are defined in
  `services/data-separation/access-information-interface/access-information-interface-chart/templates/configmap.yaml`.
  A right reaches the token as a claim such as `kaapana.ai/applications: ["launch_<project id>"]`. OPA checks
  these claims and not the role names (`services/kaapana-admin/auth-backend/auth-backend-chart/files/auth-policies.rego`).
- Rights for applications exist already: `open_applications`, `view_applications`, `launch_application`,
  `delete_active_apps` and `view_active_apps`. A scientist has only `open_applications`, and a principal
  investigator has all five. Today they guard routes of kube-helm.
- A new service is reachable only for admins until OPA rules for it exist
  (`services/kaapana-admin/auth-backend/auth-backend-chart/files/`). It also needs an IngressRoute for
  `/project/<id>/<service>` and an entry in the frontend lists of project-scoped services
  (`services/base/base-ui/docker/files/src/utils/httpClient.ts`).

The API mock takes the project as an explicit `project_id` instead of the `Project` header, so that it reads well
on its own. The implementation has to decide whether project-scoped routes take the project from the header, from
the path, or from both, and check that they agree. `/project/<id>/` accepts the UUID, the short id or the name of
a project. Store and compare the UUID from the `Project` header. The mocks use ids such as `lung-ct` only because
they are easy to read.

### Conventions of the newer FastAPI services

`services/base/workflow-api` is the best model to copy:

- Routes under `/v1`, plural kebab-case nouns, snake_case JSON and enums as strings. workflow-api writes some
  enum values capitalized and others in lower snake_case. The API mock uses lower snake_case for all of them.
- Errors as `{"detail": "<message>"}`, with 404 for not found, 409 for a conflict and 400 for a request that is
  well-formed but rejected. 422 comes only from FastAPI's request validation, and its `detail` is a list.
- `201` with a `Location` header for a create, `204` for a delete, `202` for work that continues in the background.
- `uvicorn --root-path $APPLICATION_ROOT` behind a Traefik `stripPrefix`, so Swagger works at `/<service>/docs`.
- The image builds `FROM local-only/base-python-cpu:latest` with the platform's pinned constraints and listens on
  port 8080.

### An older helm deployer exists

kube-helm (`services/kaapana-admin/kube-helm/docker/files/backend/app/routes.py`, for example
`/helm-install-chart` and `/helm-delete-chart`) already installs charts for the platform. Read it before writing
new helm code, and decide whether the Helm Chart Consumer replaces it. Two of its features overlap with the
concept:

- It reads the `multiinstallable_whitelist` of the project from AII, which has routes to read and replace the
  list. The whitelist limits which applications the members of a project may launch and delete, so it already
  enables applications per project (Story 5.2). Decide whether the enablement of the consumer replaces it.
- `/complete-active-application`, `/active-applications` and `/pending-applications-count` already serve the
  applications that workflows start (Epic 7).

### Every project already has a namespace

AII installs the chart `services/data-separation/project-namespace/project-namespace-chart` for every project.
Its templates create what several open decisions can build on:

- The namespace that the `Project` header names as `kubernetes_namespace`. Q6 decides whether applications run
  there.
- Network policies that deny all traffic in the namespace. A label such as `network-access-opensearch` opens one
  route for a pod, and Traefik may reach every pod. An application that calls a Kaapana API needs such a route.
- The secret `project-user-credentials` with a technical user of the project, and the secret `oidc-client-secret`.
  The credentials of an application can build on them (Q7, Story 4.5).
- A `LimitRange` with a default memory request and limit for containers. Limits per project (Story 6.1) need a
  `ResourceQuota` in addition.

## What the decisions mean for the code

### Model an application as its registered versions

Several versions of one helm-chart content can be registered at the same time (Q3). Key a registered version by
application id and version. Derive the application, its newest version and the "newer version available" marker
from the versions instead of storing them. A stored copy would have to be kept in sync with every registration.

Q14 is open: two different extensions may bring the same name and version. The mock answers 409. Settle it before
the registration route is final, because it decides the key.

### Keep the chart and the declarations of every deployment

A deployment whose version was deregistered can still change its parameters (Q4). `helm upgrade` needs the chart
as an argument. Helm stores the chart of each release in a Kubernetes secret, but reading it back needs the helm
SDK or decoding that secret, and `helm-chart-content.json` is not stored at all. Copy the chart archive and the
content at registration, because `chart_reference` can point at an extension that is uninstalled later. Keep
both while any deployment runs that version. The API mock keeps deregistered versions readable for this:
`GET /v1/applications/{id}/versions/{version}` also answers for a deregistered version.

### Make the placement a union

A deployment is either in a project, optionally for one user, or platform-wide (Q1, Q11). Model this as
`ProjectPlacement | PlatformPlacement`, as in `api-mock/app/models.py`, so that a platform-wide deployment
cannot carry a project or a "deployed for". "Deployed for" never restricts access. Every member of the project can
open every deployment of the project.

### Derive the state, do not store it

The state of a deployment comes from its helm release and the readiness of its pods (Story 3.1). Store the last
requested operation and read the rest from the cluster. A stored `state` column goes stale as soon as a pod
crashes or someone runs `helm` by hand. A reconciler compares the records with the helm releases after a restart
and marks releases that were changed or removed outside the consumer (Story 12.1). The API returns this as
`drift`. Clients learn about state changes by polling `GET /v1/deployments/{id}`. workflow-api already pushes
updates over a websocket at `/ws` (`services/base/workflow-api/docker/files/app/main.py`), which is a model
for a later push channel.

### Put every permission rule in one table

The rules are short (Story 5.1, Q2, Q11):

| Action | Scientist of the project | PI of the project | kaapana-system-admin |
|---|---|---|---|
| List, open, status | yes | yes | yes |
| Deploy, update, undeploy in the project | no | yes | yes |
| Logs | no | yes | yes |
| Complete a workflow deployment | yes | yes | yes |
| Deploy, update, undeploy platform-wide | no | no | yes |
| Enable and disable applications | no | no | yes |

Everyone may list and open platform-wide deployments. Keep this as one table that the service layer checks for
every call, and authorize an operation on one deployment against that deployment's own project. A check per route
is easy to forget on the next route. Write the permission tests from this table and the concept, not from the code.

The columns name the default roles. Check the rights in the token instead of the role names, so that the table
also holds for custom roles (Story 5.4). The existing rights fit some rows, for example `launch_application` for
deploy and `delete_active_apps` for undeploy. Other rows need new rights, for example logs.

`DeploymentCreate.workflow` marks a deployment as started by a workflow. Only workflow-api may set it. Otherwise any
principal investigator could create deployments that look like workflow steps. As with the registrations, Kaapana
has no service identity that workflow-api could use to prove who it is. The open question about callers inside the
cluster covers both. Q15 is open: may a workflow task deploy when a scientist started the run, although scientists
cannot deploy?

### Share one check sequence between dry-run and the real call

Deploy and update run the same checks in the same order, and the dry-run routes stop after them:

1. Permission for the placement.
2. The application is enabled in the project. Enabling covers all versions, and platform-wide deploys do not need
   it (Q12 is open).
3. The version is registered, and the application supports the scope.
4. Single instance: an application that is not multi-deployable has at most one deployment per project, counted
   over all versions, and at most one platform-wide.
5. The name is unique among the deployments a project lists, platform-wide ones included.
6. The values match the declarations: type, minimum and maximum, pattern, choices, and required.
7. The values are mapped onto chart values. A value that is not declared cannot be set.
8. `helm install --dry-run` or `helm upgrade --dry-run`.

If the dry-run and the real call use different code, they will disagree, and the dry-run then promises a deploy
that fails. The API mock offers the dry-run as separate routes, `POST /v1/deployments/dry-run` and
`POST /v1/deployments/{id}/dry-run`. They answer 200 with all problems and the chart values. Only a missing
permission answers 403, as in the real call. The real calls stop at the first problem and answer 400, 403 or 409.

A helm dry-run renders the chart and checks the objects against the schemas of the cluster, but it sends no
object to the API server. Admission webhooks, resource quotas, limit ranges and Pod Security therefore do not
run, and a deploy can pass the dry-run and still be refused. Limits per project (Story 6.1) and restrictions on
what a chart may create (Story 6.2) need a check of their own on the rendered manifest, for example
`kubectl apply --dry-run=server`. This holds for Helm 3, which kube-helm installs. Check it again for the helm
version that the consumer uses.

On update, parameters that exist in both versions keep their values, new ones get their defaults,
dropped ones disappear, and `null` resets a value to its default (Stories 11.3, 11.4).

### Never return a secret, and keep it out of the helm values

Responses show only whether a secret parameter is set. This includes the rendered chart values of a dry-run.

Helm stores the values of every revision in the cluster, and `helm get values` prints them. A secret that is passed
as a chart value is therefore readable by anyone who can read the helm release. The consumer writes the value into a
Kubernetes secret of its own and passes only the name of that secret to the chart. The `chart_value` of a secret
parameter names the chart value that receives this name. Document this for extension developers, because their chart
has to read the secret by its name.

### Undeploying deletes the data, and helm does not do that alone

Undeploying deletes the persistent volumes and their data (Q5), also for workflow deployments and admin
undeploys. `helm uninstall` does not delete the PVCs that a StatefulSet creates from `volumeClaimTemplates`, and
it keeps resources annotated with `helm.sh/resource-policy: keep`. The consumer has to delete those PVCs itself.
Whether the data on the disk is gone also depends on the reclaim policy of the storage class. Define which PVCs
belong to a deployment, for example by a label that the consumer passes to every chart. `helm uninstall` also keeps
what a hook created, unless the hook has a delete policy.

The container diagram in `concept.md` gives the consumer read-only access to Kubernetes. Deleting PVCs needs
write access, and so does writing the secrets of secret parameters. The service account of the consumer needs
these rights in every namespace it deploys to, and the diagram has to follow this decision.

### Pass the same platform values to every chart

Every deploy passes the values that the platform owns, so that charts can rely on them (Stories 4.3, 4.4, 4.5):

- a unique release name and a name prefix for Kubernetes objects,
- the URL path of the web interface, for settings like JupyterLab's `base_url`,
- the project id, its bucket and its namespace (Q6 decides the namespace),
- the credentials of the project's technical user or a dedicated client (Q7). They have the rights of a scientist
  of the project.

Document these values for extension developers together with the schema of `helm-chart-content.json`.

### Make every repeatable call converge

Registering the same version twice, deregistering twice, undeploying a deployment that is already undeploying, and
completing a workflow deployment twice must each end in the same state. The Extension Manager and the workflow
tasks retry.

Deregistering a version that is not registered answers 204. Undeploy and complete answer 404 once the deployment is
gone, because an unknown id can also be a mistake. A client that retries takes this 404 as success.

### Let project management ask before deleting a project

Deleting a project is refused while it has deployments (Q9). The project management in AII has to ask the consumer
first, for example with `GET /v1/deployments?project_id=<id>`. Platform-wide deployments never block. The AII side
does not exist yet.

The check and the deletion are two steps, and a deploy between them leaves a deployment in a deleted project. Close
this gap, for example by archiving the project before the check and refusing deploys in an archived project.

### Give workflow deployments a durable outcome

A workflow task deploys an application, waits, and continues when the user completes the work (Epic 7). The task
needs to read the outcome, finished or abandoned, after the deployment is gone. The API mock does not model this
yet, because `POST /v1/deployments/{id}/complete` undeploys and the record then disappears. Either keep completed
workflow deployments readable with their outcome, or tell workflow-api directly. Undeploy the deployment when its
task fails, is retried or times out (Story 7.4).

## Open questions

- Q6: one namespace per project, per deployment, or shared. This decides the conflict rules of Story 4.3.
- Q12: whether a new version of an enabled application starts disabled.
- Q13: on whose behalf a platform-wide application acts.
- Q14: what identifies a helm-chart content across extensions.
- Q15: whether a workflow may deploy when a scientist started it.
- How the chart reaches the consumer from the Extension Manager.
- How callers inside the cluster, such as the Extension Manager and workflow-api, prove who they are.
- How the Extension Manager keeps and shows the failure reason of a registration.
- How versions are ordered when the version of an extension is not a semantic version. The API mock orders them
  as semantic versions.
- Whether a parameter can take its choices from the project, such as the folders of its bucket, and whether a
  mapping can add a unit to a value. The UI mock shows both, and the API mock has neither.
- How a workflow task learns the outcome of a workflow deployment after the deployment is gone.
- Whether names have to be unique across a project's deployments and all platform-wide ones, as the mocks assume,
  or only per scope.

## A possible order for the MVP

1. `HelmChartInstaller` in the Extension Manager, and register and deregister in the consumer.
2. Enablement per project and the list of deployable applications.
3. Deploy with the check sequence and the helm dry-run, and the state derived from the release and the pods.
4. The web interface behind the gateway: IngressRoute, OPA rules and the platform values.
5. Undeploy, including the PVCs.
6. The reconciler for restarts and drift.
7. The deletion check in AII.
