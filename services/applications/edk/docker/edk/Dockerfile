FROM local-only/base-python-gpu:latest

LABEL IMAGE="edk"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

# install skopeo for copying containers from/to registries https://github.com/containers/skopeo
RUN apt-get update -y && apt-get -y install skopeo

RUN mkdir -p /kaapana/app/kaapana
RUN mkdir -p /kaapana/app/dag
RUN mkdir -p /kaapana/app/utils

COPY files/utils /kaapana/app/utils
COPY files/init.sh /kaapana/app

RUN pip install -r /kaapana/app/utils/requirements.txt

RUN chmod +x /kaapana/app/init.sh

# ENTRYPOINT ["/app/utils/init.sh"]