FROM local-only/base-ui:latest AS base-ui

FROM docker.io/node:lts-alpine3.23 AS build-stage

LABEL IMAGE="extension-manager-ui"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/extension-manager-ui/docker/files
COPY --from=base-ui /kaapana/base-ui/docker/files/package.json /kaapana/base-ui/docker/files/package.json
COPY --from=base-ui /kaapana/base-ui/docker/files/dist /kaapana/base-ui/docker/files/dist
COPY files/package*.json ./
RUN npm install -g npm@11.16.0 && npm ci
COPY files .

################################
######### DEVELOPMENT ##########
################################
# EXPOSE 5173
# CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

################################
######### PRODUCTION ###########
################################
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.31-alpine
WORKDIR /kaapana/app

COPY --from=build-stage /kaapana/extension-manager-ui/docker/files/dist /kaapana/app
COPY --from=build-stage /kaapana/extension-manager-ui/docker/files/nginx.conf /etc/nginx/nginx.conf

USER 1000
