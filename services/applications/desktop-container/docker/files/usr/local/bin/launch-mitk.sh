#!/bin/bash
# Desktop-container launcher for MITK Workbench (target of mitk.desktop).
# MITK restores a saved window geometry that is often pinned to (0,0); at (0,0) openbox draws the
# window's title bar at y=-26 — off the top edge — so the app looks undecorated even though it is
# decorated. Maximize the main window once it maps: as a WM-managed state, openbox computes an
# on-screen frame (title bar visible) and re-flows it on each Selkies RANDR resize, overriding
# whatever geometry MITK restored. Unlike the mitk-workbench (a single-app kiosk that goes
# fullscreen/borderless in startMITK.sh), here MITK is one windowed app among several, so it stays
# decorated. If a window is already up, just raise it instead of spawning a second instance.
if wmctrl -l | grep -q 'Research'; then
	wmctrl -a 'Research'
	exit 0
fi

/mitk/MitkWorkbench.sh &
PID=$!

echo 'Waiting for MITK window to maximize'
for i in $(seq 1 120); do
	wmctrl -l | grep -q 'Research' && break
	sleep 1
done
wmctrl -r 'Research' -b add,maximized_vert,maximized_horz

wait $PID
