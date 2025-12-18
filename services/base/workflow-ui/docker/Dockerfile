FROM local-only/base-landing-page:latest AS base-landing-resource


FROM node:lts-alpine3.19 AS build-stage

WORKDIR /app

COPY ./files ./

COPY --from=base-landing-resource /kaapana/app/public/favicon.ico ./public/favicon.ico
COPY --from=base-landing-resource /kaapana/app/src/assets/img/kaapana.png ./public/assets/img/logo.png
RUN yarn install

LABEL IMAGE="workflow-ui"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

################################
######### DEVELOPMENT ##########
################################
# EXPOSE 5173
# CMD ["yarn", "dev", "--host", "0.0.0.0", "--port", "5173"]


################################
######### PRODUCTION ###########
################################
RUN yarn build

FROM nginx:1.29.3-alpine

RUN mkdir /app
COPY --from=build-stage /app/dist /app
COPY --from=build-stage /app/nginx.conf /etc/nginx/nginx.conf