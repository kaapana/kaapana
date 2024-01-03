FROM docker.io/node:21-alpine3.17 

LABEL IMAGE="spe-frontend"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/spe-vue/package*.json ./

RUN npm install
COPY files/spe-vue/ .

RUN npm i vuetify
RUN npm i vite-plugin-vuetify
RUN npm i @mdi/font
RUN npm i vuex
RUN npm i axios


# # build stage
# FROM docker.io/node:lts-alpine3.16 as build-stage

# LABEL REGISTRY="local-only"
# LABEL IMAGE="base-landing-page"
# LABEL VERSION="latest"
# LABEL BUILD_IGNORE="False"

# WORKDIR /kaapana/app
# COPY files/kaapana_app/package*.json ./
# RUN npm install

# COPY files/kaapana_app .
#  registry.hzdr.de/jens.beyermann/jens-dev/spe-frontend:0.0.0-latest
#  registry.hzdr.de/jens.beyermann/jens-dev/spe-frontend:0.0.0-latest