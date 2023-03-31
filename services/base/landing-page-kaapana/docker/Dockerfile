FROM local-only/base-landing-page:latest as build-stage

LABEL IMAGE="landing-page-kaapana"
LABEL VERSION="0.1.3"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

RUN npm run build

# # # ###############################
# # # ############# Dev #############
# # # ###############################
# # # # In the landing-page deployment, adjust the resource limits to at least 12Gi and change the docker image to the one you are pushing 
# COPY files/dev.sh .
# # RUN chmod +x dev.sh
# CMD ["/bin/sh", "dev.sh"]
# # ###############################

###############################
######### Production ##########
###############################
FROM docker.io/nginx:1.19.3-alpine

# Create a user "kaapana" with minimal rights
RUN adduser -D -H -u 1000 -s /bin/sh kaapana

WORKDIR /kaapana/app

# RUN mkdir -p /kaapana/app
COPY --from=build-stage /kaapana/app/dist /kaapana/app
COPY --from=build-stage /kaapana/app/nginx.conf /etc/nginx/nginx.conf

# Set "nginx" as the owner of the /kaapana/app directory
RUN chown -R nginx:nginx /kaapana/app && \
    chown -R nginx:nginx /var/cache/nginx && \
    mkdir -p /var/run/nginx && chown -R nginx:nginx /var/run/nginx
    
# Switch to the "nginx" user for security reasons
USER nginx

