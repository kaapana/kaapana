FROM alpine/git:v2.34.2 as build-stage

LABEL IMAGE="doccano-frontend"
LABEL VERSION="sha-0489118"
                   
LABEL CI_IGNORE="False"

WORKDIR /

# git hack to replace git:// with https:// -> dkfz proxy 
RUN git config --global url."https://".insteadOf git://

RUN git clone https://github.com/klauskades/doccano.git doccano && cd doccano && git checkout 8044a025c699eb7a75bde5fad921923e8ef78b4e
# && git checkout bf3f3e647fbf00749deebe571326d8d728805639

FROM node:16.11.1-alpine3.13 AS frontend-builder

ENV SUB_URL='/doccano'
COPY --from=build-stage /doccano/frontend/ /app/
RUN sed -i 's/line-height: 70px !important;//' /app/components/tasks/sequenceLabeling/EntityItemBox.vue
COPY files/nuxt.config.js /app/
# COPY files/pages/projects/_id/upload/index.vue /app/pages/projects/_id/upload/
# COPY files/pages/projects/_id/text-classification/index.vue /app/pages/projects/_id/text-classification
# COPY files/pages/projects/_id/sequence-to-sequence/index.vue /app/pages/projects/_id/sequence-to-sequence
# COPY files/components/configAutoLabeling/form/FileField.vue /app/components/configAutoLabeling/form/
# COPY files/domain/models/example/example.ts /app/domain/models/example

WORKDIR /app
RUN apk add --no-cache git

RUN git config --global url."https://".insteadOf git://
RUN apk add -U --no-cache python3 make g++ \
  && yarn install
RUN yarn build \
  && apk del --no-cache git make g++

FROM nginx:1.21.1-alpine AS runtime
ENV SUB_URL='/doccano'
COPY --from=frontend-builder /app/dist /var/www/html/doccano
COPY files/nginx/nginx.conf /etc/nginx/nginx.conf
COPY files/nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080