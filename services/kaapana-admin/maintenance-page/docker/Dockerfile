# # # ###############################
# # # ############# Build ###########
# # # ###############################

FROM node:lts-alpine3.16 as build-stage

WORKDIR /maintenance/app
COPY files/kaapana_app/package*.json ./
RUN npm install

COPY files/kaapana_app .


LABEL IMAGE="maintenance-page-kaapana"
LABEL VERSION="0.1.3"
LABEL CI_IGNORE="False"

RUN npm run build

# # # ###############################
# # # ############# Dev #############
# # # ###############################
# # # # In the maintenance-page deployment, adjust the resource limits to at least 12Gi and change the docker image to the one you are pushing 
# WORKDIR / 
# COPY files/dev.sh .
# # RUN chmod +x dev.sh
# CMD ["/bin/sh", "dev.sh"]
# # ###############################

###############################
######### Production ##########
###############################
FROM nginx:1.19.3-alpine

RUN mkdir /app
COPY --from=build-stage /maintenance/app/dist /app/maintenance
COPY --from=build-stage /maintenance/app/nginx.conf /etc/nginx/nginx.conf

