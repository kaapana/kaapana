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

The Docker fixture at
`processing-container/tasks/predict-body-parts-task.json` uses a CPU-only command
override for local Task API testing. The production processing-container
template remains GPU-enabled.

Build the standalone image with the repository build CLI:

```bash
kaapana-build \
  --default-registry REGISTRY \
  --registry-username USER \
  --registry-password TOKEN \
  --build-ignore-patterns "*templates_and_examples/*,*ci/*,*lib/task_api/*,*-backup/*" \
  --containers-to-build bodypartregression-task-api
```

The final ignore entry keeps the preserved `bodypart-regression-task-backup`
Dockerfile out of build discovery without modifying the backup itself.
