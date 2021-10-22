#!/bin/bash

sed -i "s+^.*NotebookApp.base_url.*$+c.NotebookApp.base_url = '$INGRESS_PATH'+g" /root/.jupyter/jupyter_notebook_config.py
sed -i "s+^.*NotebookApp.notebook_dir.*$+c.NotebookApp.notebook_dir = '/appdata'+g" /root/.jupyter/jupyter_notebook_config.py
jupyter lab --ip=* --port=8888 --no-browser --allow-root