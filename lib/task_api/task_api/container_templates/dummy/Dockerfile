FROM python:3.12-slim

LABEL IMAGE="dummy"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /home/dummy
COPY files/upstream.py /home/dummy/
COPY files/downstream.py /home/dummy/
