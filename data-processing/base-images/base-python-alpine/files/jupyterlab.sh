#!/bin/bash

sed -i "s+^.*ServerApp.base_url.*$+c.ServerApp.base_url = '$INGRESS_PATH'+g" /root/.jupyter/jupyter_lab_config.py
sed -i "s+^.*ServerApp.root_dir.*$+c.ServerApp.root_dir = '/kaapanasrc'+g" /root/.jupyter/jupyter_lab_config.py
sed -i "s+^.*ServerApp.quit_button.*$+c.ServerApp.quit_button = False+g" /root/.jupyter/jupyter_lab_config.py # hide quit button, as quitting the app causes the pod to shut down, triggering a kubernetes CrashLoopBackoff

jupyter lab --ip=* --port=8888 --no-browser --allow-root