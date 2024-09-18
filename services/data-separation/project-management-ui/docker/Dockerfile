FROM local-only/base-landing-page:latest AS base-landing-resource


FROM node:lts-alpine3.19 AS build-stage

WORKDIR /app
COPY ./files ./
COPY --from=base-landing-resource /kaapana/app/public/favicon.ico ./public/favicon.ico
COPY --from=base-landing-resource /kaapana/app/src/assets/img/kaapana.png ./public/assets/img/logo.png
RUN yarn install

LABEL IMAGE="project-management-ui"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"

RUN yarn build

FROM nginx:1.25.4-alpine

RUN mkdir /app
COPY --from=build-stage /app/dist /app
COPY --from=build-stage /app/nginx.conf /etc/nginx/nginx.conf