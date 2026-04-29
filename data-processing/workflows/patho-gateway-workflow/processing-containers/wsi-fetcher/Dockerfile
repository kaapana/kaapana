FROM local-only/base-python-cpu:latest

LABEL IMAGE="wsi-fetcher"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /home/kaapana
COPY files/fetch_wsi.py /home/kaapana/
