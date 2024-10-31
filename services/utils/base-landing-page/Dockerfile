# build stage
FROM docker.io/node:lts-alpine3.19 as build-stage

LABEL REGISTRY="local-only"
LABEL IMAGE="base-landing-page"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

RUN apk add --update python3 make g++\
   && rm -rf /var/cache/apk/*
COPY files/kaapana_app/package*.json ./
RUN npm install -g npm@10.3.0 && npm install
COPY files/kaapana_app .
