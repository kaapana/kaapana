FROM local-only/base-python-cpu:latest

LABEL IMAGE="data-api-finetune-train"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /home/kaapana
COPY files/dummy_train.py /home/kaapana/
