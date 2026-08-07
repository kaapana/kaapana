FROM docker.io/node:lts-alpine3.23 AS build-stage

LABEL IMAGE="portal-ui"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

WORKDIR /app

COPY ./files/package*.json ./
RUN npm install -g npm@11.16.0 && npm ci
COPY ./files ./

################################
######### DEVELOPMENT ##########
################################
# EXPOSE 5173
# CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]


################################
######### PRODUCTION ###########
################################
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.31-alpine
WORKDIR /kaapana/app

COPY --from=build-stage /app/dist /kaapana/app
COPY --from=build-stage /app/nginx.conf /etc/nginx/nginx.conf
USER 0
RUN chown 1000 /etc/nginx/nginx.conf

USER 1000
