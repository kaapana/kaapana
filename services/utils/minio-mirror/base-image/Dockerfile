FROM local-only/base-python-cpu:latest
LABEL REGISTRY="local-only"
LABEL IMAGE="base-minio-mc"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

RUN curl https://dl.min.io/client/mc/release/linux-amd64/archive/mcli_20240307003149.0.0_amd64.deb \
  -o mcli.deb && \
  dpkg -i mcli.deb

RUN useradd -u 1000 kaapana && \
  mkdir -p /home/kaapana/ && chown kaapana /home/kaapana/ && \
  cp /usr/local/bin/mcli /usr/local/bin/mc && \
  chmod 110 /usr/local/bin/mc && \
  chown 1000:1000 /usr/local/bin/mc

USER 1000