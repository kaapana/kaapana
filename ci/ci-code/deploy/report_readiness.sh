#!/usr/bin/env bash
# Prints the readiness table target_readiness.yaml fetched from the target and
# decides the job's fate.
#
# On the runner, not in ansible: a `fail` task wraps its message in an error
# block with a YAML source excerpt and a fatal JSON dump, which buries the one
# thing the reader wants. Here the table is plain (colored) job-log output and
# the verdict is the last line.
set -euo pipefail

artifacts_dir="${1:-${ARTIFACTS_DIR:-artifacts}}"
log="$artifacts_dir/target_readiness.log"
report="$artifacts_dir/target_readiness.json"

if [ ! -s "$log" ] || [ ! -s "$report" ]; then
  echo "No readiness report ($report). The check did not run on the target — see the ansible output above." >&2
  exit 1
fi

echo
cat "$log"
echo

if python3 -c "import json,sys; sys.exit(0 if json.load(open('$report'))['ready'] else 1)"; then
  exit 0
fi

echo "Fix the 'failed' rows above, or re-run the pipeline with '-i exec_server_installation:true' to let the server installation prepare the target instead." >&2
exit 1
