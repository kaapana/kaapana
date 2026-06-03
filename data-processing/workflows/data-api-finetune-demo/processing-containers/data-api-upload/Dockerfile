FROM local-only/base-python-cpu:latest

LABEL IMAGE="data-api-upload"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /home/kaapana
COPY files/upload_to_data_api.py /home/kaapana/
