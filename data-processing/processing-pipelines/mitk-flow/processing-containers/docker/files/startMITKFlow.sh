#!/bin/bash
echo "Fixing input data permissions"
sudo chown $USER -R /$WORKFLOW_DIR/$BATCH_NAME

echo "Starting MTIK Flow"
/mitk-flow/MitkFlowBench.sh /$WORKFLOW_DIR/$BATCH_NAME/tasklist.json &
PID=$!

tail -f  $USER/logfile | while read LOGLINE
do
	[[ "${LOGLINE}" == *"BlueBerry Workbench ready"* ]] && pkill -P $$ tail
done

echo 'Setting fullscreen mode'
wmctrl -r 'Segmentation' -b toggle,fullscreen

wait $PID