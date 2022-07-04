#!/bin/bash
export INGRESS_PATH='klaus'
sed -i "s+^.*ServerApp.base_url.*$+c.ServerApp.base_url = '$INGRESS_PATH'+g" /root/.jupyter/jupyter_lab_config.py
sed -i "s+^.*ServerApp.root_dir.*$+c.ServerApp.root_dir = '/kaapanasrc'+g" /root/.jupyter/jupyter_lab_config.py

jupyter lab --ip=* --port=8888 --no-browser --allow-root