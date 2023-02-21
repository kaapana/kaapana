FROM python:3.9.16-slim

LABEL REGISTRY="local-only"
LABEL IMAGE="base-python-cpu"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /kaapana

COPY files/requirements.system /kaapana/
RUN apt-get update -q -y && apt-get install -y --no-install-recommends apt-utils && \
    cat /kaapana/requirements.system | xargs apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Common Python packages
COPY files/requirements.txt /kaapana/
RUN python -m pip install --upgrade setuptools pip && pip3 install -r /kaapana/requirements.txt

# Code server
RUN wget https://code-server.dev/install.sh
RUN /bin/bash install.sh --version 4.2.0
RUN code-server --install-extension ms-python.python

# Juyterlab
# Disable security token for Jupyter lab
RUN jupyter-lab --generate-config \
 && sed -i "s/^.*ServerApp.token.*$/c.ServerApp.token = ''/g" /root/.jupyter/jupyter_lab_config.py
COPY files/jupyterlab.sh /
COPY files/kaapana_federated /kaapana_federated

WORKDIR /app
