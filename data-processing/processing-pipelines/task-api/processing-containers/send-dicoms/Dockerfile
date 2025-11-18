FROM local-only/base-python-cpu:latest

LABEL IMAGE="send-dicoms"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /home/kaapana

COPY files/send-dicoms.sh /home/kaapana/
