#!/bin/sh

# Use the passed WORKSPACE DIRECTORY - otherwise use /workspace
if [ -z "${WORKSPACE_DIR}" ]; then
  WORKSPACE="/appdata"
else
  WORKSPACE="${WORKSPACE_DIR}"
fi
cd $WORKSPACE

### launch the corresponding process ###
if [ "$1" = "jupyter" ]
then
        # run jupyter notebook
        sed -i "s+^.*NotebookApp.base_url.*$+c.NotebookApp.base_url = '$INGRESS_PATH'+g" /root/.jupyter/jupyter_notebook_config.py
        jupyter notebook --ip=`cat /etc/hosts |tail -n 1|cut -f 1` --port=8888 --allow-root
        # place data owner / sicentist example
        #mv example appdata/
fi

if [ "$1" = "network" ]
then
        # start sift network
        syft-network
fi