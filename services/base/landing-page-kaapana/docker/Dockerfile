FROM local-only/base-landing-page:latest as build-stage

LABEL IMAGE="landing-page-kaapana"
LABEL VERSION="0.1.3"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

RUN npm run build

###############################
######### Production ##########
###############################
FROM docker.io/nginx:1.23.3-alpine

WORKDIR /kaapana/app

# RUN mkdir -p /kaapana/app
COPY --from=build-stage /kaapana/app/dist /kaapana/app
COPY --from=build-stage /kaapana/app/nginx.conf /etc/nginx/nginx.conf

