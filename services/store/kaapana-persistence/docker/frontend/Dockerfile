FROM node:lts-alpine3.19 as build-stage

WORKDIR /app
COPY . ./
RUN yarn install

LABEL IMAGE="kaapana-persistence-frontend"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"

RUN yarn build

FROM nginx:1.25.4-alpine

RUN mkdir /app
COPY --from=build-stage /app/dist /app
COPY --from=build-stage /app/nginx.conf /etc/nginx/nginx.conf

