echo '==============================='
echo 'Run an awesome MITK Application'
echo '==============================='
echo "mitk" | sudo -S chown mitk:mitk -R /$WORKFLOW_DIR/$BATCH_NAME

/mitk/MitkFlowBench.sh /$WORKFLOW_DIR/$BATCH_NAME/worklist.json
PID=$!
# wait until Workbench is ready
tail -f  /home/mitk/Desktop/logfile | while read LOGLINE
do
	[[ "${LOGLINE}" == *"BlueBerry Workbench ready"* ]] && pkill -P $$ tail
done
echo 'Setting fullscreen mode'
wmctrl -r 'Segmentation' -b toggle,fullscreen
# wait for process to end, before starting new process
wait $PID
#clear logfile
> /home/mitk/Desktop/logfile