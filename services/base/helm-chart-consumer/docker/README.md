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

- **Story references**: marks UI elements with the IDs of the stories (and open questions) they cover.
- **User stories**: lists the covered stories. "Show me" switches to a fitting person, opens the view and
  highlights the place.
- **⋮ menu**: *Concept options* lets you try answers to open questions Q5, Q8 and Q9.
  *Simulate platform restart* reloads the list (Story 12.1). Also dark mode and *Reset mock data*.

## Views and stories

The mock covers 17 of the 24 MVP stories. As requested, it leaves out the stories about the Extension Manager
(1.1, 1.2) and about developing extensions (4.1–4.5).

| View (shell menu) | Who | Stories |
|---|---|---|
| Workflows › Applications | Project members | 2.4 open, 3.1 status, 5.1, 5.3, 8.3, 12.1, 2.3 undeploy (row menu) |
| Application details | Project members | 2.3, 2.5, 2.6, 2.7, 3.1, 3.2, 5.3, 8.1, 8.2, 12.1 |
| Workflows › Application Catalog | PI, admin | 2.1, 8.1, 5.2 |
| Deploy form | PI, admin | 2.1, 2.2, 8.1, 8.2, 8.3 |
| System › Application Availability | Admin | 5.2 (and Q8) |
| System › Projects | Admin | 12.2 (and Q9); stand-in for the project management view |

Things to try: deploy JupyterLab with a GPU and 40 GiB memory (the dry-run rejects it), deploy a second CVAT
(blocked: one instance per project), open an application as Anna, then *Try a link from another project*.

## Choices the mock makes visible

The concept leaves these open. The mock picks one answer so it can be discussed:

- Two views, following the container diagram: *Applications* (deployed instances, for everyone in the project)
  and *Application Catalog* (deploying, for PIs). Undeploy sits in *Applications*, next to the instance it removes.
- Q1 (ownership): the deploy form has a *For* field that names a scientist. Access stays project-wide.
- Every deploy runs a dry-run first. *Check configuration* runs it on its own.
- A deploy with a GPU asks for confirmation, because the GPU stays reserved while the application runs.
- Releases changed or removed outside Kaapana are flagged. A removed one can be taken off the list.
- Q5, Q8 and Q9 can be switched in *Concept options*.

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
