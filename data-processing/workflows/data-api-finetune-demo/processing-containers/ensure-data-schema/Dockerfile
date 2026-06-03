FROM local-only/base-python-cpu:latest

LABEL IMAGE="data-api-ensure-schema"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /home/kaapana
COPY files/ensure_data_schema.py /home/kaapana/
