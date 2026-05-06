FROM local-only/base-python-cpu:latest

LABEL IMAGE="wsi-fetcher"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /kaapana/app
COPY files/fetch_wsi.py /kaapana/app
