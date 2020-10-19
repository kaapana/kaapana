echo '==============================='
echo 'Run an awesome MITK Application'
echo '==============================='
for dir in /$WORKFLOW_DIR/$BATCH_NAME/*/    # list directories in the form "/tmp/dirname/"
do
        INPUTDIR="$dir"
        OUTPUTDIR="$dir$OPERATOR_OUT_DIR"
        echo ${INPUTDIR}
        echo ${OUTPUTDIR}
	echo "mitk" | sudo -S chown mitk:mitk -R $INPUTDIR
	if [ -d "$OUTPUTDIR" ]; then
	    echo "$OUTPUTDIR exist"
	else 
	    echo "$OUTPUTDIR does not exist"
	    mkdir $OUTPUTDIR
	fi
        /mitk/bin/MitkFlowBench /$INPUTDIR/input.mitksceneindex --flow.outputdir $OUTPUTDIR --flow.outputextension dcm &
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
done


