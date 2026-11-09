# Helm Chart Consumer UI mock

A click-through mock of the user interface described in [../concept.md](../concept.md) (ticket #2449). It shows
how the UI could support the MVP user stories. It is a mock only: no API calls, all data lives in the browser tab,
and a reload starts from the seed data again.

## Run it

```bash
cd services/base/helm-chart-consumer/docker
docker compose up --build
```

Open http://localhost:5050. Stop it with `docker compose down`.

The compose file also builds the shared `local-only/base-ui` image that the Dockerfile starts from, so no
kaapana-build run is needed. The image is labelled `BUILD_IGNORE="True"`, so platform builds skip it.

For a dev server with hot reload, build base-ui once (`npm ci && npm run build` in
`services/base/base-ui/docker/files`), then run `npm ci && npm run dev` in `docker/files`.

## Using the mock

The dark bar at the top belongs to the mock, not to the proposed UI:

- **Viewing as**: switch between three people. Menu entries and actions follow their role in the selected
  project (Story 5.1).

  | Person | Role |
  |---|---|
  | Paul Weber | Principal investigator of Lung CT Study, scientist in Brain MRI Cohort |
  | Anna Schmidt | Scientist in Lung CT Study and Brain MRI Cohort |
  | Kim Novak | Kaapana system admin |

- **Story references**: marks UI elements with the IDs of the stories they cover, and of the questions in
  [../QandA.md](../QandA.md) whose answers they show.
- **User stories**: lists the covered stories. "Show me" switches to a fitting person, opens the view and
  highlights the place.
- **⋮ menu**: *Simulate platform restart* reloads the list (Story 12.1). Also dark mode and *Reset mock data*.

## Views and stories

The mock covers 18 of the 24 MVP stories. As requested, it leaves out registering in the Extension Manager (1.1)
and developing extensions (4.1–4.5). Of Story 1.2 it shows only the marker on deployed applications whose version is
no longer registered. Where an answer in QandA.md cannot be shown otherwise, it also covers parts of the Release 2
stories 9.1 and 9.2 (platform-wide applications, Q11) and 11.1 (registered versions, Q3).

| View (shell menu) | Who | Stories |
|---|---|---|
| Workflows › Applications | Project members | 2.4 open, 3.1 status, 5.1, 5.3, 8.3, 9.2, 11.1, 12.1, 1.2 marker, 2.3 undeploy (row menu) |
| Application details | Project members | 1.2, 2.3, 2.5, 2.6, 2.7, 3.1, 3.2, 5.3, 8.1, 8.2, 9.2, 12.1 |
| Workflows › Application Catalog | PI, admin | 2.1, 8.1, 5.2, 9.1, 11.1 |
| Deploy form | PI, admin | 2.1, 2.2, 8.1, 8.2, 8.3, 9.1, 11.1 |
| System › Application Availability | Admin | 5.2 (and Q8, Q12) |
| System › Projects | Admin | 12.2 (and Q9); stand-in for the project management view |

Things to try:

- As Paul, deploy JupyterLab. The newest version, 4.3.0, is preselected. Switch to 4.2.5: the idle-kernel parameter
  disappears and the other values stay. A GPU with 40 GiB memory makes the dry-run fail.
- As Paul, deploy a second CVAT (blocked: one instance per project, whatever the version).
- As Kim, deploy Collabora Online and choose *Platform-wide*. Switch to another project: it is listed there too.
- As Anna, open *ohif* (platform-wide) and *anna-notebook*, then *Try a link from another project* on its details.
- As Kim, delete *Lung CT Study* in System › Projects. The deletion is refused and names the applications.

## Choices the mock makes visible

Answers from QandA.md, and the defaults that concept.md proposes where an answer leaves details open:

- Several versions of an application can be registered at once (Q3). The catalog shows them, the deploy form
  preselects the newest one, and a deployed application whose version is no longer registered keeps running and is
  marked. A newer registered version is only a marker; updating is Release 2.
- Only principal investigators and Kaapana system admins deploy (Q2). If an application supports both scopes, only
  a Kaapana system admin chooses between the project and platform-wide (Q11). Platform-wide applications are listed
  in every project, every user can open them, and only admins undeploy them.
- The *For* field names the whole project or one member. Every member can open every application of the project
  (Q1).
- Undeploying deletes the persistent volumes and the data on them (Q5). The dialog says so.
- An application acts on behalf of its project with the permissions of a scientist (Q7). For platform-wide
  applications this is not decided yet (Q13). Namespaces are not decided yet either (Q6), so the mock shows none.
- New applications start disabled in all projects (Q8). Enabling covers all registered versions; whether a new
  version starts disabled is not decided yet (Q12).
- Deleting a project with deployed applications is refused, and the refusal names them (Q9).
- Two views, following the container diagram: *Applications* (deployed instances, for everyone in the project)
  and *Application Catalog* (deploying, for PIs). Undeploy sits in *Applications*, next to the instance it removes.
- Every deploy runs a dry-run first. *Check configuration* runs it on its own.
- A deploy with a GPU asks for confirmation, because the GPU stays reserved while the application runs.
- Releases changed or removed outside Kaapana are flagged. A removed one can be taken off the list.

## base-ui guidelines followed

- The shared theme, fonts and icon map, via `createKaapanaVuetify` and `kaapanaIcons`.
- `ConfirmDialog` for destructive and high-impact actions; `ErrorDetailsDialog` for dry-run failures.
- One primary action per area. Destructive actions use `error`. Unavailable actions stay visible with a tooltip
  that explains why.
- Empty states that tell apart "nothing yet", "nothing matched" and "not available to you".
- Transient toasts for the outcome of an action, inline alerts for conditions of the content shown, and the shell's
  notification bell for a deployment that becomes ready.
- Validation messages that name the field and say how to fix the value.
- Dialog widths 400 / 600 / 900. Loading shows on the control that started it.
- Unsaved changes in the deploy form: the shell asks before you leave.
