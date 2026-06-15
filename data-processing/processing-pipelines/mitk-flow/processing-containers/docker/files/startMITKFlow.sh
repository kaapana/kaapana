#!/bin/bash
echo "Fixing input data permissions"
sudo chown $USER -R /$WORKFLOW_DIR/$BATCH_NAME

echo "Starting MTIK Flow"
/mitk-flow/MitkFlowBench.sh /$WORKFLOW_DIR/$BATCH_NAME/tasklist.json &
PID=$!

until grep -q "BlueBerry Workbench ready" $HOME/logfile 2>/dev/null; do
	sleep 1
done

echo 'Setting fullscreen mode'
for i in $(seq 1 30); do
	wmctrl -l | grep -q 'Segmentation' && break
	sleep 1
done
wmctrl -r 'Segmentation' -b add,fullscreen

wait $PID