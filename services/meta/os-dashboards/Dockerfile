ARG NODE_VERSION=14.20.0
FROM node:${NODE_VERSION} AS base

LABEL CI_IGNORE="True"

USER node

WORKDIR /home/node
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.2/install.sh | bash
RUN git clone https://github.com/opensearch-project/OpenSearch-Dashboards && cd OpenSearch-Dashboards && git checkout 2.2
WORKDIR /home/node/OpenSearch-Dashboards
RUN yarn osd bootstrap

USER root
ADD workflow-trigger /home/node/OpenSearch-Dashboards/plugins/workflow-trigger
RUN cd /home/node/OpenSearch-Dashboards/plugins/workflow-trigger && yarn build --opensearch-dashboards-version 2.2.0 --allow-root