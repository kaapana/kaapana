FROM local-only/base-python-cpu:latest

LABEL IMAGE="data-api-download"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /home/kaapana
COPY files/get_input_from_data_api.py /home/kaapana/
