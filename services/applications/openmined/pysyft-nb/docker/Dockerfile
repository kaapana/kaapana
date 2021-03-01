FROM openmined/pysyft-notebook

LABEL IMAGE="pysyft-nb"
LABEL VERSION="0.1.0-vdev"
LABEL CI_IGNORE="False"

# Disable security token for Jupyter lab
RUN jupyter notebook --generate-config \
 && sed -i "s/^.*NotebookApp.token.*$/c.NotebookApp.token = ''/g" /root/.jupyter/jupyter_notebook_config.py

RUN pip uninstall -y syft

# pysyft v0.2.9
RUN python -m pip install git+https://github.com/OpenMined/PySyft.git@3852ca9e78d5163b52776b231f469e32e6c8be01

RUN mkdir -p /appdata
COPY files/jupyterlab.sh /

EXPOSE 8888
ENV INGRESS_PATH /pysyft
#CMD jupyter lab --ip=* --port=8888 --no-browser --notebook-dir=/opt/app/data --allow-root

ENTRYPOINT ["/bin/bash", "/jupyterlab.sh"]