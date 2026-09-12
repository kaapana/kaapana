FROM local-only/base-python-cpu:latest
LABEL IMAGE="minio-init"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

# dl.min.io and the Docker Hub images are gone; take mc from the same pinned server image
COPY --from=quay.io/minio/minio:RELEASE.2024-11-07T00-52-20Z@sha256:ac591851803a79aee64bc37f66d77c56b0a4b6e12d9e5356380f4105510f2332 /usr/bin/mc /usr/local/bin/mc

RUN adduser --uid 1000 kaapana && chmod -R 777 /home/kaapana

# World read/writable so that users with other uid's can be used by externally setting runAsUser
ENV MC_CONFIG_DIR="/home/kaapana/.mc_config"
RUN mkdir -p /home/kaapana/.mc_config && chmod -R 777 /home/kaapana/.mc_config

USER 1000
