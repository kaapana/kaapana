FROM ubuntu:20.04

LABEL REGISTRY="local-only"
LABEL IMAGE="dcmtk-base"
LABEL VERSION="3.6.4"
LABEL CI_IGNORE="False"

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    dcmtk \
    && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt
