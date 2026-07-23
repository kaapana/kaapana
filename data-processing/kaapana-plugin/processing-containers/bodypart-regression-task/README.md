# Reusable BodyPartRegression Task API container

This standalone processing container ports the pinned legacy
BodyPartRegression inference image to the Task API.

The production template is `predict-body-parts`:

- input `nrrd` at `/kaapana/app/nrrd`
- output `bpr-json` at `/kaapana/app/bpr-json`
- one `<SeriesInstanceUID>` directory per item

The small Task API adapter creates one inference model per batch and processes
every `*.nrrd` file in every item directory. Each volume is oriented to LPS with
SimpleITK, written to a temporary NIfTI for the upstream inference API, and then
discarded. The native JSON is written to the separate output channel while item
and file names are preserved.

The Docker fixture at `tasks/predict-body-parts-task.json` uses a CPU-only
command override for local Task API testing. The production
processing-container template remains GPU-enabled.

This image is a prerequisite for workflows that reference
`bodypartregression-task-api`. It is discovered by `kaapana-build`, but it is
not selected automatically by the platform's Helm build graph. Build and push
it explicitly before installing or running such a workflow:

```bash
kaapana-build \
  --default-registry REGISTRY \
  --registry-username USER \
  --registry-password TOKEN \
  --build-ignore-patterns "*templates_and_examples/*,*ci/*,*lib/task_api/*" \
  --containers-to-build bodypartregression-task-api
```
