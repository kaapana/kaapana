FROM local-only/base-python-cpu:latest

LABEL IMAGE="get-input-task"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /home/kaapana
COPY files/download_dicoms.py /home/kaapana/
