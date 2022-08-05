FROM alpine/git:v2.34.2 as build-stage

LABEL IMAGE="doccano-frontend"
LABEL VERSION="sha-0489118"
                   
LABEL CI_IGNORE="False"

WORKDIR /

# git hack to replace git:// with https:// -> dkfz proxy 
RUN git config --global url."https://".insteadOf git://

RUN git clone https://github.com/klauskades/doccano.git doccano && cd doccano && git checkout c26505ba9e05be527fd67a9fa2f4a0a2466e8708
# && git checkout bf3f3e647fbf00749deebe571326d8d728805639

FROM node:16.11.1-alpine3.13 AS frontend-builder

ENV SUB_URL='/doccano'
COPY --from=build-stage /doccano/frontend/ /app/
RUN sed -i 's/line-height: 70px !important;//' /app/components/tasks/sequenceLabeling/EntityItemBox.vue
COPY files/nuxt.config.js /app/

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
COPY files/nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080