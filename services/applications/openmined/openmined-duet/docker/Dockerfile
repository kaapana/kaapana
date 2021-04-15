FROM nvcr.io/nvidia/pytorch:20.09-py3

LABEL IMAGE="openmined-duet"
LABEL VERSION="0-1.0-vdev"
LABEL CI_IGNORE="False"

# Disable security token for Jupyter lab
RUN jupyter notebook --generate-config \
 && sed -i "s/^.*NotebookApp.token.*$/c.NotebookApp.token = ''/g" /root/.jupyter/jupyter_notebook_config.py

RUN pip uninstall -y syft

# pysyft v0.3.0
RUN python -m pip install --no-cache-dir git+https://github.com/OpenMined/PySyft.git@b7a52b513a9150a968a59b44d92c406cae05bed8

COPY files/bootstrap.sh /

RUN mkdir -p /example
COPY ["files/notebooks/data-scientist.ipynb", "files/notebooks/data-owner.ipynb", "/example/"]

ENTRYPOINT ["/bin/bash", "/bootstrap.sh"]