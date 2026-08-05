FROM local-only/base-python-cpu:latest
LABEL REGISTRY="local-only"
LABEL IMAGE="base-rclone"
LABEL VERSION="2026-08-03"
LABEL CI_IGNORE="False"

RUN curl https://rclone.org/install.sh | bash

# World read/writable so that users with other uid's can be used by extrnally setting runAsUser
RUN adduser --uid 1000 kaapana && chmod -R 777 /home/kaapana

USER 1000