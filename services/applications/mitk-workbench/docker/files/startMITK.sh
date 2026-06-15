#!/bin/bash
echo "Starting MITK Workbench"
/mitk/MitkWorkbench.sh &
PID=$!

echo 'Setting fullscreen mode'
for i in $(seq 1 60); do
	wmctrl -l | grep -q 'Research' && break
	sleep 1
done
wmctrl -r 'Research' -b add,fullscreen

wait $PID



