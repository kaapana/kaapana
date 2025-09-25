#!/usr/bin/env bash
set -euo pipefail

TESTCASE_DIR=${KAAPANA_DIR}/data-processing
TIMEOUT=300

mkdir -p "${ARTIFACTS_DIR}/tests/"

pids=()   # store PIDs
names=()  # store test names

for test in $( find $TESTCASE_DIR -wholename *ci-config/*.yaml)
do
    name=$(basename -s ".yaml" $test)
    logfile="${ARTIFACTS_DIR}/tests/${name}.log"
    echo "Start test for $name"
    (
        timeout $TIMEOUT python3 $KAAPANA_DIR/ci/ci-code/test/src/integration_tests.py --files ${test} --host ${ip_address} > "${logfile}" 2>&1
    ) &
    pid=$!
    pids+=("$pid")
    names+=("$name")
done

all_successfull=0
# wait for all jobs to finish and print their logs
for i in "${!pids[@]}"; do
    pid=${pids[$i]}
    name=${names[$i]}
    logfile="${ARTIFACTS_DIR}/tests/${name}.log"

    if wait "$pid"; then
        echo -e "\n[OK] Test $name finished successfully"
    else
        all_successfull=1
        rc=$?
        if [ $rc -eq 124 ]; then
            echo -e "\n[TIMEOUT] Test $name exceeded ${TIMEOUT}s"
        else if [ $rc -eq 0 ]; then
            echo -e "\n[OK] Test $name finished successfully"
        else
            echo -e "\n[FAIL] Test $name failed (exit code $rc)"
        fi
    fi

    echo "========== Logs for $name =========="
    cat "$logfile"
    echo "===================================="
done

exit $all_successfull