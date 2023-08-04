# build stage
FROM docker.io/node:lts-alpine3.16 as build-stage

LABEL REGISTRY="local-only"
LABEL IMAGE="base-landing-page"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app
COPY files/kaapana_app/package*.json ./
RUN npm install

COPY files/kaapana_app .
