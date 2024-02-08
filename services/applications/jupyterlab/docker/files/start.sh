#!/bin/bash
set -eu

# Disable security token for Jupyter lab
sed -i "s/^.*ServerApp.token.*$/c.ServerApp.token = ''/g" /kaapana/app/.jupyter/jupyter_lab_config.py

sed -i "s+^.*ServerApp.base_url.*$+c.ServerApp.base_url = '$INGRESS_PATH'+g" /kaapana/app/.jupyter/jupyter_lab_config.py
sed -i "s+^.*ServerApp.root_dir.*$+c.ServerApp.root_dir = '/kaapana'+g" /kaapana/app/.jupyter/jupyter_lab_config.py

# hide quit button, as quitting the app causes the pod to shut down, triggering a kubernetes CrashLoopBackoff
sed -i "s+^.*ServerApp.quit_button.*$+c.ServerApp.quit_button = False+g" /kaapana/app/.jupyter/jupyter_lab_config.py

# disable the webpdf export option, as requirements of it are currently not supported
echo -e "\nc.WebPDFExporter.enabled = False" >>/kaapana/app/.jupyter/jupyter_lab_config.py 

jupyter lab --ip=* --port=8888 --no-browser --config /kaapana/app/.jupyter/jupyter_lab_config.py