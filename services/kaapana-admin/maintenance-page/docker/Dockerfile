# # # ###############################
# # # ############# Build ###########
# # # ###############################

FROM docker.io/node:lts-alpine3.20 AS build-stage

LABEL IMAGE="maintenance-page-kaapana"
LABEL VERSION="0.2.1"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app
COPY files/kaapana_app/package*.json ./
RUN npm install -g npm@10.9.0 && npm install

COPY files/kaapana_app .


RUN npm run build

# # # ###############################
# # # ############# Dev #############
# # # ###############################
# # # # In the maintenance-page deployment, adjust the resource limits to at least 12Gi and change the docker image to the one you are pushing 
# USER 0
# RUN chown -R 1000:1000 /kaapana/app && \
#     ln -s /kaapana/app/jsons /kaapana/app/public

# USER 1000
# WORKDIR /kaapana/app

# RUN npm run build

# CMD ["npm", "run", "serve"]
# # ###############################

###############################
######### Production ##########
###############################
FROM nginxinc/nginx-unprivileged:1.27.2-alpine

WORKDIR /kaapana/app

COPY --from=build-stage /kaapana/app/dist /app/maintenance
COPY --from=build-stage /kaapana/app/nginx.conf /etc/nginx/nginx.conf
USER 0
RUN chown 1000 /etc/nginx/nginx.conf

USER 1000
