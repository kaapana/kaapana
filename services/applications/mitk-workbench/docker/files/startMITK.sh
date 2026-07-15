#!/bin/bash
echo "Starting MITK Workbench"
/mitk/MitkWorkbench.sh &
PID=$!

# Wait for the main MITK window ('Research - MITK Workbench ...') to map, then make it fullscreen.
# The previous readiness check grepped $HOME/logfile, which is never written (supervisord tees to
# $HOME/mitk-logfile), so it hung here forever and the window step was never reached — leaving
# the window stranded off-screen after Selkies' RANDR display resize. That was the readiness bug,
# not fullscreen itself: as a WM-managed state, fullscreen is re-flowed by openbox on each RANDR
# resize just like maximized, so with the window-detection loop below it can't end up stranded.
# Fullscreen (not maximized): this is a single-app kiosk, so we want MITK borderless — no title bar
# and no panel — filling the whole viewport. Matches mitk-flow's startMITKFlow.sh.
echo 'Setting fullscreen mode'
for i in $(seq 1 120); do
	wmctrl -l | grep -q 'Research' && break
	sleep 1
done
wmctrl -r 'Research' -b add,fullscreen

wait $PID



