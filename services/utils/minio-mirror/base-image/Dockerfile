FROM local-only/base-python-cpu:latest
LABEL REGISTRY="local-only"
LABEL IMAGE="base-minio-mc"
LABEL VERSION="2024-11-17"
LABEL CI_IGNORE="False"


RUN curl https://dl.min.io/client/mc/release/linux-amd64/mcli_20241117193525.0.0_amd64.deb \
  -o mcli.deb && \
  dpkg -i mcli.deb && \
  ln -s /usr/local/bin/mcli /usr/local/bin/mc


RUN adduser --uid 1000 kaapana && chmod -R 777 /home/kaapana

# World read/writable so that users with other uid's can be used by extrnally setting runAsUser
ENV MC_CONFIG_DIR="/home/kaapana/.mc_config"
RUN mkdir -p /home/kaapana/.mc_config && chmod -R 777 /home/kaapana/.mc_config

USER 1000