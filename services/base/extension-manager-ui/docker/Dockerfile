FROM docker.io/node:22.13.0-alpine3.20  AS build-stage

WORKDIR /app

COPY ./files ./

RUN npm install -g npm@11.16.0 && npm ci

LABEL IMAGE="extension-manager-ui"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

################################
######### DEVELOPMENT ##########
################################
# EXPOSE 5173
# CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]


################################
######### PRODUCTION ###########
################################
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.31.2-alpine

USER 0
RUN mkdir /app && chown 1000 /app
COPY --from=build-stage /app/dist /app
COPY --from=build-stage /app/nginx.conf /etc/nginx/nginx.conf
RUN chown 1000 /etc/nginx/nginx.conf

USER 1000