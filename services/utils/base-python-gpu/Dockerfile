FROM nvcr.io/nvidia/pytorch:22.02-py3
# FROM pytorchlightning/pytorch_lightning:base-cuda-py3.9-torch1.11

LABEL REGISTRY="local-only"
LABEL IMAGE="base-python-gpu"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    git \
    htop \
    zip \
    unzip

# Common Python packages
RUN python -m pip install --upgrade pip
COPY files/requirements.txt /root/
RUN pip3 install -r /root/requirements.txt

# Code server
RUN wget https://code-server.dev/install.sh
RUN /bin/bash install.sh --version 4.2.0
RUN code-server --install-extension ms-python.python

# Juyterlab
# Only for jupyternotebook: jupyter nbconvert --to html --no-input ...
RUN apt-get install -y texlive-xetex texlive-fonts-recommended texlive-plain-generic pandoc
# Disable security token for Jupyter lab
RUN jupyter notebook --generate-config \
 && sed -i "s/^.*NotebookApp.token.*$/c.NotebookApp.token = ''/g" /root/.jupyter/jupyter_notebook_config.py
COPY files/jupyterlab.sh /

WORKDIR /kaapanasrc