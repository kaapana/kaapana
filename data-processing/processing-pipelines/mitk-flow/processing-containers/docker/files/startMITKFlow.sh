#!/bin/bash
echo "Fixing input data permissions"
sudo chown $USER -R /$WORKFLOW_DIR/$BATCH_NAME

echo "Starting MTIK Flow"
/mitk-flow/MitkFlowBench.sh /$WORKFLOW_DIR/$BATCH_NAME/tasklist.json &
PID=$!

# Wait for the main MITK FlowBench window ('Segmentation - MITK FlowBench ...') to map, then make
# it fullscreen. Poll for the window directly (version-independent) rather than grepping the log
# for a specific "ready" string (which hangs forever if that message ever changes); loading the
# tasklist/input data can take a while, so allow up to ~2 min instead of 30 s.
echo 'Waiting for MITK FlowBench window to set fullscreen'
for i in $(seq 1 120); do
	wmctrl -l | grep -q 'Segmentation' && break
	sleep 1
done
wmctrl -r 'Segmentation' -b add,fullscreen

wait $PID