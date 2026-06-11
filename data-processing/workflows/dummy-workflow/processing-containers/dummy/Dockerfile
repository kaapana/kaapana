FROM local-only/base-python-cpu:latest

LABEL IMAGE="dummy"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /kaapana/app
COPY files/upstream.py /kaapana/app/
COPY files/downstream.py /kaapana/app/
