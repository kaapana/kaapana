#!/usr/bin/env bash
# Prints the path of the SSH private key the deploy jobs log into the target
# with, after fixing its permissions. Sourced from the before_script of every
# job that runs ansible against the deployment target.
#
# DEPLOYMENT_SSH_KEY wins over CI_SSH_PRIVATE_KEY, so a run can target a
# machine the shared CI key has no access to (e.g. a developer's own box).
# Both forms of the variable work:
#   File type  — the value is the path the runner wrote the key to
#   plain type — the value is the key itself, pasted into the Run pipeline form
set -euo pipefail

key="${DEPLOYMENT_SSH_KEY:-}"
[ -n "$key" ] || key="${CI_SSH_PRIVATE_KEY:-}"
if [ -z "$key" ]; then
  echo "No SSH key: set DEPLOYMENT_SSH_KEY for this run, or the CI_SSH_PRIVATE_KEY project variable." >&2
  exit 1
fi

if [ ! -f "$key" ]; then
  path="$(mktemp)"
  # A key without the trailing newline is rejected by ssh as malformed.
  printf '%s\n' "${key%$'\n'}" >"$path"
  key="$path"
fi

# ssh refuses group/world-readable keys; File variables arrive too open.
chmod 600 "$key"
printf '%s\n' "$key"
