FROM local-only/base-python-cpu:latest

LABEL IMAGE="dsf-exporter"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /home/kaapana
COPY files/export.py /home/kaapana/
