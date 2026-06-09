#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for all pipeline jobs to reach a terminal state..."
while true; do
    ACTIVE_COUNT=$(curl -sf \
        --header "JOB-TOKEN: $CI_JOB_TOKEN" \
        "$CI_API_V4_URL/projects/$CI_PROJECT_ID/pipelines/$CI_PIPELINE_ID/jobs?per_page=100" \
        | python3 -c "
import sys, json
jobs = json.load(sys.stdin)
active = [j['name'] for j in jobs
          if j['stage'] not in ('clean',)
          and j['status'] in ('running', 'pending', 'waiting_for_resource', 'preparing', 'created')]
print(len(active))
for name in active:
    print('  still active: ' + name, file=sys.stderr)
")
    echo "Active jobs outside clean stage: $ACTIVE_COUNT"
    [[ "$ACTIVE_COUNT" == "0" ]] && break
    sleep 30
done

if [[ "$DEPLOYMENT_INSTANCE_PROVISIONER" == "openstack" ]]; then
    echo "Deleting VM with OpenStack"
    ansible-playbook -i localhost, "$CI_PROJECT_DIR/ci/ci-code/deploy/delete_openstack_vm.yaml"
else
    echo "Deleting VM with Harvester"
    ansible-playbook -i localhost, "$CI_PROJECT_DIR/ci/ci-code/deploy/delete_harvester_vm.yaml"
fi
