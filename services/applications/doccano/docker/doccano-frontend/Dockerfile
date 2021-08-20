FROM python:3.9-alpine3.12 as build-stage

LABEL IMAGE="doccano-frontend"
LABEL VERSION="sha-50db4e9"
LABEL CI_IGNORE="False"

RUN apk add --no-cache git

# git hack to replace git:// with https:// -> dkfz proxy 
RUN git config --global url."https://".insteadOf git://
RUN git clone https://github.com/doccano/doccano.git doccano && cd doccano && git checkout 50db4e9f367592c44b85b4f20a3a0cf7aa5582bd

FROM node:13.7-alpine AS frontend-builder

COPY --from=build-stage /doccano/frontend/ /app/
RUN sed -i 's/line-height: 70px !important;//' /app/components/tasks/sequenceLabeling/EntityItemBox.vue
COPY files/nuxt.config.js /app/
COPY files/pages/projects/_id/upload/index.vue /app/pages/projects/_id/upload/
COPY files/components/configAutoLabeling/form/FileField.vue /app/components/configAutoLabeling/form/
COPY files/domain/models/example/example.ts /app/domain/models/example

WORKDIR /app
RUN apk add --no-cache git

RUN git config --global url."https://".insteadOf git://
RUN apk add -U --no-cache python3 make g++ \
  && yarn install \
  && yarn build \
  && apk del --no-cache git make g++

FROM nginx:1.17.4-alpine AS runtime

COPY --from=frontend-builder /app/dist /var/www/html/doccano
COPY files/nginx/nginx.conf /etc/nginx/nginx.conf
COPY files/nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080