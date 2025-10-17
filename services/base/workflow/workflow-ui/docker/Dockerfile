FROM local-only/base-landing-page:latest AS base-landing-resource
FROM node:lts-alpine3.19 AS build-stage

WORKDIR /app

COPY ./files/package*.json ./
RUN npm ci

COPY ./files ./
COPY --from=base-landing-resource /kaapana/app/public/favicon.ico ./public/favicon.ico
COPY --from=base-landing-resource /kaapana/app/src/assets/img/kaapana.png ./public/assets/img/logo.png

# For development, skip build and run Vite
# Uncomment this block for dev:
EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# # Build the production app
# RUN npm run build

# # Serve via Nginx
# FROM nginx:stable-alpine AS production
# COPY --from=build-stage /app/dist /usr/share/nginx/html
# COPY ./files/nginx.conf /etc/nginx/conf.d/default.conf

# EXPOSE 80
# CMD ["nginx", "-g", "daemon off;"]