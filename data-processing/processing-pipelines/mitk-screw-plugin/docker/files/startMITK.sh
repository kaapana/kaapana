echo '==============================='
echo 'Set nnunet model dirs as environment variables'
echo '==============================='
#nnunetv1: verse model
export RESULTS_FOLDER="/kaapana/models/mitk-screw-plugin/verse"
#nnunetv2: screw model
export nnUNet_results="/kaapana/models/mitk-screw-plugin/screws"


echo '==============================='
echo 'Run an awesome MITK Application'
echo '==============================='
cd /mitk
env QTWEBENGINE_DISABLE_SANDBOX=1 ./MitkWorkbench.sh &
PID=$!
# wait until Workbench is ready
tail -f  /root/Desktop/logfile | while read LOGLINE
do
	[[ "${LOGLINE}" == *"BlueBerry Workbench ready"* ]] && pkill -P $$ tail
done
echo 'Setting fullscreen mode'
wmctrl -r 'Research' -b toggle,fullscreen
# wait for process to end, before starting new process
wait $PID
#clear logfile
> /root/Desktop/logfile



