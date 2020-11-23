# build stage
FROM node:lts-alpine as build-stage

LABEL REGISTRY="local-only"
LABEL IMAGE="airflow-app"
LABEL VERSION="0.1.0-vdev"
LABEL CI_IGNORE="False"

WORKDIR /airflow/app
COPY files/airflow-app/package*.json ./
RUN npm install
RUN npm install local-storage-fallback
COPY files/airflow-app .

LABEL IMAGE="airflow-app-kaapana"
LABEL VERSION="0.1.2-vdev"
LABEL CI_IGNORE="False"

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
COPY --from=build-stage /airflow/app/dist /app
COPY --from=build-stage /airflow/app/nginx.conf /etc/nginx/nginx.conf
