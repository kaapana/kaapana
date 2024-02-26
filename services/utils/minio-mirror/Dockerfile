FROM local-only/base-minio-mc:latest
LABEL IMAGE="minio-mirror"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/start.sh /kaapana/app/


CMD ["/usr/bin/bash","/kaapana/app/start.sh"]