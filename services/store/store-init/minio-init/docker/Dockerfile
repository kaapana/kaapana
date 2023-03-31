FROM docker.io/minio/mc:RELEASE.2022-03-31T04-55-30Z
LABEL IMAGE=minio-init
LABEL VERSION=2022.03.31
LABEL CI_IGNORE="False"

COPY files/minio.sh .
RUN chmod +x minio.sh
COPY files/readme.txt .
ENTRYPOINT ["/bin/sh", "minio.sh"]