FROM local-only/base-python-cpu:latest
LABEL REGISTRY="local-only"
LABEL IMAGE="base-minio-mc"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

<<<<<<< HEAD
RUN curl https://dl.min.io/client/mc/release/linux-amd64/archive/mcli_20240118070339.0.0_amd64.deb \
=======
RUN curl https://dl.min.io/client/mc/release/linux-amd64/archive/mcli_20240128162314.0.0_amd64.deb \
>>>>>>> Use latest version of minio mc.
  -o mcli.deb && \
  dpkg -i mcli.deb

RUN useradd -u 1000 kaapana && \
    mkdir -p /home/kaapana/ && chown kaapana /home/kaapana/ && \
    cp /usr/local/bin/mcli /usr/local/bin/mc && \
    chmod 110 /usr/local/bin/mc && \
    chown 1000:1000 /usr/local/bin/mc

USER 1000