# build stage
FROM docker.io/node:lts-alpine3.16 as build-stage

LABEL REGISTRY="local-only"
LABEL IMAGE="base-landing-page"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app
COPY files/kaapana_app/package*.json ./
RUN npm install

COPY files/kaapana_app .

# # # ###############################
# # # ############# Dev #############
# # # ###############################
# # # In the landing-page deployment, adjust the resource limits to at least 12Gi and change the docker image to the one you are pushing 
# RUN npm run build
# WORKDIR / 
# COPY files/dev.sh .
# # RUN chmod +x dev.sh
# CMD ["/bin/sh", "dev.sh"]
# # ###############################

# ###############################
# ######### Production ##########
# ###############################
# FROM nginx:1.19.3-alpine

# RUN mkdir /kaapana/app
# COPY --from=build-stage /kaapana/app/dist /kaapana/app
# COPY files/kaapana_app/nginx.conf /etc/nginx/nginx.conf

# # # ###############################
