FROM local-only/base-python-cpu:latest

COPY files/ /kaapana/app/

LABEL IMAGE="minio-mirror"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/start.sh /kaapana/app/

RUN curl https://dl.min.io/client/mc/release/linux-amd64/mc.RELEASE.2024-01-18T07-03-39Z \
  -o /usr/local/bin/mc

RUN useradd -u 1000 kaapana && \
    mkdir -p /home/kaapana/ && chown kaapana /home/kaapana/ && \
    chmod 110 /usr/local/bin/mc && \
    chown 1000:1000 /usr/local/bin/mc

USER 1000

CMD ["/usr/bin/bash","/kaapana/app/start.sh"]