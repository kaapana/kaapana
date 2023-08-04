FROM docker.io/minio/mc:RELEASE.2022-03-31T04-55-30Z
LABEL IMAGE=minio-init
LABEL VERSION=2022.03.31
LABEL CI_IGNORE="False"

COPY files/ /kaapana/app/
RUN chmod +x /kaapana/app/minio.sh
ENTRYPOINT ["/bin/sh", "/kaapana/app/minio.sh"]