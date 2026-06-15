FROM docker.io/node:22.15.0 AS builder

LABEL IMAGE="os-dashboards"
LABEL VERSION="3.6.0"
LABEL BUILD_IGNORE="False"

USER root
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    zip \
    && rm -rf /var/lib/apt/lists/*

USER node
WORKDIR /home/node
RUN git clone https://github.com/opensearch-project/OpenSearch-Dashboards --depth 1 --branch 3.6.0
WORKDIR /home/node/OpenSearch-Dashboards
RUN yarn osd bootstrap

COPY files/workflow-trigger /home/node/OpenSearch-Dashboards/plugins/workflow-trigger
WORKDIR /home/node/OpenSearch-Dashboards/plugins/workflow-trigger

USER root
RUN git config --global --add safe.directory /home/node/OpenSearch-Dashboards
RUN yarn build --opensearch-dashboards-version 3.6.0 --allow-root

# ################################################################## NEW STAGE ########################################################################
FROM docker.io/opensearchproject/opensearch-dashboards:3.6.0

WORKDIR /usr/share/opensearch-dashboards/
COPY --from=builder /home/node/OpenSearch-Dashboards/plugins/workflow-trigger/build/workflowTrigger-3.6.0.zip /workflowTrigger.zip

RUN bin/opensearch-dashboards-plugin install file:///workflowTrigger.zip
COPY files/kaapana.svg /usr/share/opensearch-dashboards/src/core/server/core_app/assets/kaapana.svg
COPY files/kaapana_mono.svg /usr/share/opensearch-dashboards/src/core/server/core_app/assets/kaapana_mono.svg
COPY files/kaapana_mono_2.svg /usr/share/opensearch-dashboards/src/core/server/core_app/assets/kaapana_mono_2.svg
COPY files/loading.png /usr/share/opensearch-dashboards/src/core/server/core_app/assets/loading.png

USER root
RUN dnf upgrade libcap nspr nss-softokn nss-softoken-freebl nss-sysinit nss-util curl-minimal libcurl-minimal ncurses-base ncurses-libs openssl-libs python3-pip-wheel sqlite-libs --security --assumeyes --releasever=latest
USER opensearch-dashboards
