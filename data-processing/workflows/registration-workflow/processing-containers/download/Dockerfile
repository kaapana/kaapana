FROM local-only/base-python-cpu:latest

LABEL IMAGE="get-input-task"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /kaapana/app
COPY files/download_dicoms.py /kaapana/app/
