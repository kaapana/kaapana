FROM local-only/base-python-gpu:latest

LABEL IMAGE="edk"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

RUN mkdir -p /kaapana/app/kaapana
RUN mkdir -p /kaapana/app/dev/dag
RUN mkdir -p /kaapana/app/utils

COPY files/utils /kaapana/app/utils
# COPY files/requirements.txt /kaapana/app/dev/dag/

RUN chmod +x /kaapana/app/utils/init.sh

# ENTRYPOINT ["/app/utils/init.sh"]