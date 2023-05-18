ARG NODE_VERSION=14.20.1
FROM docker.io/node:${NODE_VERSION} AS builder

LABEL IMAGE="os-dashboards"
LABEL VERSION="2.2.0"
LABEL CI_IGNORE="False"

USER root
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    zip \
    && rm -rf /var/lib/apt/lists/*

USER node
WORKDIR /home/node
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.2/install.sh | bash
RUN git clone https://github.com/opensearch-project/OpenSearch-Dashboards && cd OpenSearch-Dashboards && git checkout 2.6
WORKDIR /home/node/OpenSearch-Dashboards
RUN yarn osd bootstrap

COPY files/workflow-trigger /home/node/OpenSearch-Dashboards/plugins/workflow-trigger
WORKDIR /home/node/OpenSearch-Dashboards/plugins/workflow-trigger

USER root
RUN yarn build --opensearch-dashboards-version 2.6.0 --allow-root

# ################################################################## NEW STAGE ########################################################################
FROM docker.io/opensearchproject/opensearch-dashboards:2.6.0

WORKDIR /usr/share/opensearch-dashboards/
COPY --from=builder /home/node/OpenSearch-Dashboards/plugins/workflow-trigger/build/workflowTrigger-2.6.0.zip /workflowTrigger.zip
RUN bin/opensearch-dashboards-plugin install file:///workflowTrigger.zip
COPY files/kaapana.svg /usr/share/opensearch-dashboards/src/core/server/core_app/assets/kaapana.svg
COPY files/kaapana_mono.svg /usr/share/opensearch-dashboards/src/core/server/core_app/assets/kaapana_mono.svg
COPY files/kaapana_mono_2.svg /usr/share/opensearch-dashboards/src/core/server/core_app/assets/kaapana_mono_2.svg
COPY files/loading.png /usr/share/opensearch-dashboards/src/core/server/core_app/assets/loading.png

RUN /usr/share/opensearch-dashboards/bin/opensearch-dashboards-plugin remove securityDashboards
# # COPY --chown=opensearch-dashboards:opensearch-dashboards opensearch_dashboards.yml /usr/share/opensearch-dashboards/config/

