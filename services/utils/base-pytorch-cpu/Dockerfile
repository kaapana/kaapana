# Same python version as in pytorch-gpu
FROM python:3.8.10

LABEL REGISTRY="local-only"
LABEL IMAGE="base-pytorch-cpu"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    git \
    htop \
    zip \
    unzip

# Only for jupyternotebook: jupyter nbconvert --to html --no-input ...
RUN apt-get install -y texlive-xetex texlive-fonts-recommended texlive-plain-generic pandoc

# Common Python packages
RUN python -m pip install --upgrade pip
COPY files/requirements.txt /root/
RUN pip3 install -r /root/requirements.txt

# Code server
RUN wget https://code-server.dev/install.sh
RUN /bin/bash install.sh --version 4.2.0
RUN code-server --install-extension ms-python.python

# Juyterlab
# Disable security token for Jupyter lab
RUN jupyter notebook --generate-config \
 && sed -i "s/^.*NotebookApp.token.*$/c.NotebookApp.token = ''/g" /root/.jupyter/jupyter_notebook_config.py
COPY files/jupyterlab.sh /
