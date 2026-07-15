#!/bin/bash
# Launcher target for the desktop/menu entry. MITK already auto-starts via supervisord, so if a
# window is already up we just raise it instead of spawning a second instance; otherwise we start
# it (fullscreen handling lives in startMITK.sh).
if wmctrl -l | grep -q 'Research'; then
	wmctrl -a 'Research'
else
	/mitk/startMITK.sh
fi
