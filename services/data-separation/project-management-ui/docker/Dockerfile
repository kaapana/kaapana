FROM local-only/base-landing-page:latest AS base-landing-resource


FROM docker.io/node:22.13.0-alpine3.20  AS build-stage

WORKDIR /app

COPY ./files ./

COPY --from=base-landing-resource /kaapana/app/public/favicon.ico ./public/favicon.ico
COPY --from=base-landing-resource /kaapana/app/src/assets/img/kaapana.png ./public/assets/img/logo.png

RUN npm install -g npm@11.16.0 && npm ci

LABEL IMAGE="project-management-ui"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

################################
######### DEVELOPMENT ##########
################################
# EXPOSE 5174
# CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5174"]


################################
######### PRODUCTION ###########
################################
RUN npm run build

FROM nginx:1.31.2-alpine

RUN mkdir /app
COPY --from=build-stage /app/dist /app
COPY --from=build-stage /app/nginx.conf /etc/nginx/nginx.conf