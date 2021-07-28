FROM python:3.9-alpine3.12 as build-stage

LABEL IMAGE="doccano-frontend"
LABEL VERSION="sha-50db4e9"
LABEL CI_IGNORE="False"

RUN apk add --no-cache git

RUN git clone https://github.com/doccano/doccano.git doccano && cd doccano && git checkout 50db4e9f367592c44b85b4f20a3a0cf7aa5582bd

FROM node:13.7-alpine AS frontend-builder

COPY --from=build-stage /doccano/frontend/ /app/
COPY files/nuxt.config.js /app/

WORKDIR /app

RUN apk add -U --no-cache git python3 make g++ \
  && yarn install \
  && yarn build \
  && apk del --no-cache git make g++

FROM nginx:1.17.4-alpine AS runtime

RUN addgroup -g 61000 doccano \
  && adduser -G doccano -S doccano -u 61000

COPY --chown=doccano:doccano --from=frontend-builder /app/dist /var/www/html/doccano
COPY files/nginx/nginx.conf /etc/nginx/nginx.conf
COPY files/nginx/default.conf /etc/nginx/conf.d/default.conf

RUN chown -R doccano:doccano /var/cache/nginx \
  && chmod -R g+w /var/cache/nginx \
  && chown -R doccano:doccano /media

EXPOSE 8080

USER doccano:doccano