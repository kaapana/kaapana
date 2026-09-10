# CI troubleshooting

Most jobs upload their logs and reports as artifacts (job page → **Browse**) —
look there before re-running. The tail of the log is artifact-upload logging. A failure on `develop` opens a GitLab issue with the collected `*.log` artifacts and posts to Slack (`if_ci_failing`), unless the run targeted a host of your own
(`DEPLOYMENT_INSTANCE_FQDN` set).

Starting runs and the inputs behind them: [README.md](../README.md).

## Symptoms

| Symptom | Likely cause / what to do |
|---|---|
| Job stuck "pending" | No runner with the required tag is picking it up |
| Job dies in *prepare*: `failed to pull image … access forbidden` | `DOCKER_AUTH_CONFIG` has no valid entry for the active registry host ([internals.md](internals.md#docker_auth_config)) |
| A job hits the 5-minute `.test_template` cap | The suite got slower, or the runner is slower than the cap assumes. Split the suite, or raise `timeout:` on the job |
| `build_packages` fails immediately | Registry login (`CI_REGISTRY_*`) or the build VM's docker daemon. Full log in the `build.log` artifact |
| `build_packages` fails on one image | Search the trace for `Build failed!` — the line is prefixed with the image tag, and the docker output follows under `LOG:`. Usually reproducible with `kaapana-build` locally |
| `prepare_deployment`: `kaapana-admin-chart '<tag>' not found in …` | The commit was never built and pushed. The check runs before any VM is created. Build it first |
| `preflight_target`: `existing_platform` FATAL | A platform is already deployed there. Undeploy it (`./kaapanactl.sh deploy --undeploy`), or re-run with `exec_redeploy:bool(true)` — that demotes the check to a warning and undeploys first |
| Integration test failed, deployment VM already gone | Re-run with `exec_destroy_delayed:bool(true)`, then SSH in |
| `ui_tests` fails | Download the Playwright HTML report artifact — it has traces and screenshots |
| `run_workflows` fails | The assertion prints `Workflow <name> failed:` and the kaapana-backend job records. For Airflow logs, keep the platform alive and open `https://<vm-fqdn>/flow`. |