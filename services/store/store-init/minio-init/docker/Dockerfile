# FROM docker.io/minio/mc:RELEASE.2022-03-31T04-55-30Z
# LABEL IMAGE=minio-init
# LABEL VERSION=2022.03.31
# LABEL CI_IGNORE="False"

FROM local-only/base-minio-mc:latest
LABEL IMAGE="minio-init"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/ /kaapana/app/
USER 0
RUN chmod +x /kaapana/app/minio.sh
USER 1000
ENTRYPOINT ["/bin/sh", "/kaapana/app/minio.sh"]