FROM node:lts-alpine3.19 AS build-stage

WORKDIR /app

COPY ./ ./

RUN npm install -g npm@11.16.0 && npm ci

LABEL IMAGE="data-ui"
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

FROM nginx:1.31-alpine

RUN apk update && apk upgrade libxml2

RUN mkdir /app
COPY --from=build-stage /app/dist /app
COPY --from=build-stage /app/nginx.conf /etc/nginx/nginx.conf