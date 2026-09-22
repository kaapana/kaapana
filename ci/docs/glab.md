# Driving the CI from the terminal

[`glab`](https://gitlab.com/gitlab-org/cli) starts and inspects real pipelines
on GitLab from the CommandLine.
See CI configurations: [README.md](../README.md#Configuration-reference).


```bash
glab ci run -b my-branch \
  -i 'exec_unit_tests:bool(false)' \
  -i 'exec_integration_tests:bool(false)' \
  --variables DEPLOYMENT_INSTANCE_FQDN:my-host.dkfz-heidelberg.de
```

| Flag | Passes |
|---|---|
| `-i key:value` | one input, repeatable. Booleans need the cast: `-i 'exec_build:bool(false)'` |
| `--variables KEY:VALUE` | one variable, repeatable |
| `--variables-file KEY:path` | a File-type variable (an SSH key, a kubeconfig) |
| `-f, --variables-from file.json` | many variables, and the only way to pass a value containing a comma |
| `-b` | the branch or tag; defaults to the checked-out branch |
| `-w` | open the pipeline in a browser |

`--variables-from` takes a JSON list:

```json
[
  { "key": "DEPLOYMENT_INSTANCE_FQDN", "value": "e230-pc11.inet.dkfz-heidelberg.de", "variable_type": "env_var" },
  { "key": "DEPLOYMENT_INSTANCE_USER", "value": "ubuntu", "variable_type": "env_var" }
]
```

Watching and inspecting a run:
```bash
glab ci status -b my-branch --live               # watch it
glab ci retry <JOB_ID>                           # one job, not the pipeline

P=projects/kaapana%2Fkaapana
glab api "$P/pipelines/<ID>/jobs?per_page=100"   # job ids, stages, statuses
glab api "$P/jobs/<ID>/trace"                    # full log
glab api "$P/jobs/<ID>/artifacts" > artifacts.zip
```

## Common runs

Each line is one pipeline; the same values go into the **Run pipeline** form.

```bash
# unit tests and lint only
glab ci run -b my-branch -i 'exec_build:bool(false)' \
  -i 'exec_deploy:bool(false)' -i 'exec_integration_tests:bool(false)'

# build only
glab ci run -b my-branch -i 'exec_unit_tests:bool(false)' \
  -i 'exec_deploy:bool(false)' -i 'exec_integration_tests:bool(false)'

# deploy onto a host you own — walkthrough in local-ci.md scenario 2
glab ci run -b my-branch -i 'exec_server_installation:bool(false)' \
  --variables DEPLOYMENT_INSTANCE_FQDN:my-host.dkfz-heidelberg.de \
  --variables DEPLOYMENT_INSTANCE_USER:$USER

# one integration test job
glab ci run -b my-branch -i exec_integration_test_jobs:send_data

# keep the deployment VM 4 h to debug a failure
glab ci run -b my-branch -i 'exec_destroy_delayed:bool(true)'

# move stages to another runner — the tag has to exist on a runner
# registered to this project, see local-ci.md scenario 1
glab ci run -b my-branch -i tests_runner_tag:my-tag \
  -i build_runner_tag:my-tag -i deploy_runner_tag:my-tag
```
