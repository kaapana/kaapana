FROM local-only/base-minio-mc:latest
LABEL IMAGE="minio-mirror"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

USER 0
RUN curl https://rclone.org/install.sh | bash
RUN chmod u+s /usr/bin/rclone
USER 1000

COPY files/start.sh /kaapana/app/
COPY files/input_from_minio.txt /kaapana/app/
COPY files/output_from_application.txt /kaapana/app/
COPY files/README.txt /kaapana/app/

CMD ["/usr/bin/bash","/kaapana/app/start.sh"]