FROM local-only/base-ui:latest AS base-ui

FROM docker.io/node:lts-alpine3.23 AS build-stage

LABEL IMAGE="helm-chart-consumer-ui-mock"
LABEL VERSION="0.1.0"
# A click-through mock for the concept discussion (ticket #2449), not a platform
# component: kaapana-build must not build or push it.
LABEL BUILD_IGNORE="True"

# Recreate the repo-relative geometry so the app's
# `file:../../../base-ui/docker/files` dependency resolves in-image.
WORKDIR /kaapana/helm-chart-consumer/docker/files
COPY --from=base-ui /kaapana/base-ui/docker/files/package.json /kaapana/base-ui/docker/files/package.json
COPY --from=base-ui /kaapana/base-ui/docker/files/dist /kaapana/base-ui/docker/files/dist
COPY files/package*.json ./
RUN npm install -g npm@11.16.0 && npm ci
COPY files .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.31-alpine
WORKDIR /kaapana/app

COPY --from=build-stage /kaapana/helm-chart-consumer/docker/files/dist /kaapana/app
COPY --from=build-stage /kaapana/helm-chart-consumer/docker/files/nginx.conf /etc/nginx/nginx.conf

USER 1000
