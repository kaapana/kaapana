FROM local-only/base-python-cpu:latest
LABEL IMAGE="minio-init"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

# MinIO upstream images are gone; take mc from the pinned Silo (community MinIO fork) server image
COPY --from=docker.io/pgsty/silo:RELEASE.2026-09-16T00-00-00Z@sha256:635197cb9f36d01bee221d34d1c7d7960f6a95c48b0b6c01d99cd13bdae51a46 /usr/bin/mcli /usr/local/bin/mc

RUN adduser --uid 1000 kaapana && chmod -R 777 /home/kaapana

# World read/writable so that users with other uid's can be used by externally setting runAsUser
ENV MC_CONFIG_DIR="/home/kaapana/.mc_config"
RUN mkdir -p /home/kaapana/.mc_config && chmod -R 777 /home/kaapana/.mc_config

USER 1000
