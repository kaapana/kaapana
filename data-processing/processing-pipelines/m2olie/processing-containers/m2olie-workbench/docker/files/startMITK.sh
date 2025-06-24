#!/bin/bash
echo '==============================='
echo 'Run an awesome MITK Application'
echo '==============================='
for dir in /$WORKFLOW_DIR/$BATCH_NAME/*/    # list directories in the form "/tmp/dirname/"
do
    INPUTDIR="$dir"
    echo ${INPUTDIR}
	/m2olie/MitkWorkbench.sh $INPUTDIR/input.mitksceneindex &
	PID=$!

	tail -f  $USER/logfile | while read LOGLINE
	do
		[[ "${LOGLINE}" == *"BlueBerry Workbench ready"* ]] && pkill -P $$ tail
	done
	echo 'Setting fullscreen mode'
	wmctrl -r 'Research' -b toggle,fullscreen
	# wait for process to end, before starting new process
	wait $PID
	#clear logfile
	> $USER/logfile
done
