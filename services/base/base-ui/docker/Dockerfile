FROM docker.io/node:lts-alpine3.23 AS build-stage

LABEL REGISTRY="local-only"
LABEL IMAGE="base-ui"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

# Keep the package at the same base-ui/docker/files depth as in the repo, so
# the consuming views' `file:../../../base-ui/docker/files` dependency
# resolves identically in-image and in the source tree.
WORKDIR /kaapana/base-ui/docker/files
COPY files/package*.json ./
RUN npm install -g npm@11.16.0 && npm ci
COPY files .
RUN npm run build
