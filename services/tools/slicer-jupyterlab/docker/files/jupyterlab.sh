#!/bin/bash

sed -i "s+^.*NotebookApp.base_url.*$+c.NotebookApp.base_url = '$INGRESS_PATH'+g" /home/sliceruser/.jupyter/jupyter_notebook_config.py

jupyter notebook --ip=* --port=8888 --no-browser --notebook-dir=/home/sliceruser/work/ --allow-root