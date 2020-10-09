# build stage
FROM node:lts-alpine as build-stage

LABEL IMAGE="landing-page"
LABEL VERSION="1.1.1-vdev"
LABEL CI_IGNORE="False"

WORKDIR /landing/app
COPY files/kaapana_app/package*.json ./
RUN npm install
RUN npm install local-storage-fallback
COPY files/kaapana_app .
RUN npm run build

# ###############################
# ############# Dev #############
# ###############################
# WORKDIR / 
# COPY files/kaapana_app/dev.sh .
# RUN chmod +x dev.sh
# CMD ["/bin/sh", "dev.sh"]
# ###############################

###############################
######### Production ##########
###############################
FROM nginx:1.19.3-alpine

RUN mkdir /app
COPY --from=build-stage /landing/app/dist /app
COPY files/kaapana_app/nginx.conf /etc/nginx/nginx.conf
