FROM local-only/base-python-cpu:latest

LABEL IMAGE="send-dicoms"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /kaapana/app

COPY files/send-dicoms.sh /kaapana/app/
