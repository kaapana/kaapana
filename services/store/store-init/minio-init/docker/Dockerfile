FROM minio/mc:RELEASE.2021-03-12T03-36-59Z

LABEL IMAGE="minio-init"
LABEL VERSION="0.1.2"
LABEL CI_IGNORE="False"

COPY files/minio.sh .
RUN chmod +x minio.sh
COPY files/permissions_uploads.json .
#CMD tail -f  /dev/null
ENTRYPOINT ["/bin/sh", "minio.sh"]
#ENTRYPOINT ["/bin/sh", "minio/mc"]