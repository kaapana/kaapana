FROM local-only/base-landing-page:latest as build-stage

LABEL IMAGE="landing-page-kaapana"
LABEL VERSION="0.2.1"
LABEL BUILD_IGNORE="False"


################################
######### Development ##########
################################
# USER 0
# RUN chown 1000 /kaapana/app && \
#     ln -s /kaapana/app/jsons /kaapana/app/public && \
#     ln -s /kaapana/app/thumbnails /kaapana/app/public && \
#     chown -R 1000:1000 /kaapana/app/public
# USER 1000

# WORKDIR /kaapana/app
# RUN npm run build
# CMD ["npm", "run", "serve"]


###############################
######### Production ##########
###############################
WORKDIR /kaapana/app
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.25.3-alpine
WORKDIR /kaapana/app

COPY --from=build-stage /kaapana/app/dist /kaapana/app
COPY --from=build-stage /kaapana/app/nginx.conf /etc/nginx/nginx.conf
USER 0
RUN chown 1000 /etc/nginx/nginx.conf

USER 1000