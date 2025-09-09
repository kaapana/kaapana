FROM local-only/base-python-cpu:latest

LABEL IMAGE="dummy"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /home/dummy
COPY files/upstream.py /home/dummy/
COPY files/downstream.py /home/dummy/
