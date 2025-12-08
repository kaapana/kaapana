FROM local-only/base-mitk:latest

LABEL IMAGE="mitk-tools"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /home/kaapana

COPY files/convert.sh /home/kaapana/
COPY files/register.sh /home/kaapana/