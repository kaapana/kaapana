# build stage
FROM node:lts-alpine3.10 as build-stage

LABEL REGISTRY="local-only"
LABEL IMAGE="base-landing-page"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

WORKDIR /landing/app
COPY files/kaapana_app/package*.json ./
RUN HTTPS_PROXY="http://www-int2.dkfz-heidelberg.de:80" npm install
RUN HTTPS_PROXY="http://www-int2.dkfz-heidelberg.de:80" npm install local-storage-fallback
COPY files/kaapana_app .

# ###############################
# ############# Dev #############
# ###############################
# # In the landing-page deployment, adjust the resource limits to at least 12Gi and change the docker image to the one you are pushing 
RUN npm run build
WORKDIR / 
COPY files/kaapana_app/dev.sh .
RUN chmod +x dev.sh
COPY files/kaapana_app/setup_dev.sh .
RUN chmod +x setup_dev.sh

CMD ["/bin/sh", "dev.sh"]
###############################

# ###############################
# ######### Production ##########
# ###############################
# FROM nginx:1.19.3-alpine

# RUN mkdir /app
# COPY --from=build-stage /landing/app/dist /app
# COPY files/kaapana_app/nginx.conf /etc/nginx/nginx.conf
