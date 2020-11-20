#!/bin/sh

sed -i "s+^.*NotebookApp.base_url.*$+c.NotebookApp.base_url = '$INGRESS_PATH'+g" /root/.jupyter/jupyter_notebook_config.py

# Use the passed WORKSPACE DIRECTORY
# Otherwise use /workspace
if [ -z "${WORKSPACE_DIR}" ]; then
  WORKSPACE="/workspace"
else
  WORKSPACE="${WORKSPACE_DIR}"
fi

cd $WORKSPACE

jupyter notebook --ip=`cat /etc/hosts |tail -n 1|cut -f 1` --port=8888 --allow-root

#jupyter lab --ip=* --port=8888 --no-browser --notebook-dir=/appdata --allow-root