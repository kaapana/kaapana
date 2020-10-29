# build stage
FROM local-only/base-landing-page:0.1.0-vdev  as build-stage

LABEL IMAGE="landing-page-kaapana"
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
COPY --from=build-stage /landing/app/dist /app
COPY --from=build-stage /landing/app/nginx.conf /etc/nginx/nginx.conf

