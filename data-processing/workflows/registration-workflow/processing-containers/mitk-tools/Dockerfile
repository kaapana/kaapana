FROM local-only/base-mitk:latest

LABEL IMAGE="mitk-tools"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /kaapana/app

COPY files/convert.sh /kaapana/app/
COPY files/register.sh /kaapana/app/