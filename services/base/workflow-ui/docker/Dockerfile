FROM local-only/base-landing-page:latest AS base-landing-resource
FROM node:lts-alpine3.19 AS build-stage
WORKDIR /app

COPY ./files/package*.json ./

COPY --from=base-landing-resource /kaapana/app/public/favicon.ico ./public/favicon.ico
COPY --from=base-landing-resource /kaapana/app/src/assets/img/kaapana.png ./public/assets/img/logo.png

RUN npm ci --no-audit --prefer-offline
COPY ./files .

LABEL IMAGE="workflow-ui"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

################################
######### DEVELOPMENT ##########
################################

# Expose port 80 for dev server (match Nginx prod)
# EXPOSE 80

# Run Vite dev server with HMR
# CMD ["npx", "vite", "dev", "--host", "0.0.0.0", "--port", "80"]


################################
######### PRODUCTION ###########
################################
RUN npm run build

# FROM nginxinc/nginx-unprivileged:1.27.2-alpine
FROM nginx:1.25.4-alpine

RUN mkdir /app
COPY --from=build-stage /app/dist /app
COPY --from=build-stage /app/nginx.conf /etc/nginx/nginx.conf
