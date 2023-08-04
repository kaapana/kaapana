FROM node:lts-alpine3.16 as build-stage

WORKDIR /app
COPY . ./
RUN yarn install

LABEL IMAGE="kaapana-persistence-frontend"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="False"

RUN yarn build

FROM nginx:1.19.3-alpine

RUN mkdir /app
COPY --from=build-stage /app/dist /app
COPY --from=build-stage /app/nginx.conf /etc/nginx/nginx.conf

