FROM local-only/base-python-cpu:latest

LABEL IMAGE="dsf-exporter"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /kaapana/app
COPY files/export.py /kaapana/app/
