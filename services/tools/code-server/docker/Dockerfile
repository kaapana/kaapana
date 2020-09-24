FROM codercom/code-server:3.5.0

LABEL IMAGE="code-server"
LABEL VERSION="3.5.0-vdev"
LABEL CI_IGNORE="False"

USER root

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

USER coder


COPY files/requirements.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt

RUN curl https://extensions.coder.com/api/publishers/ms-python/vsextensions/python/2020.4.76186/vspackage --output /home/coder/vspackage
