FROM node:lts-alpine3.19 AS build-stage

WORKDIR /app
COPY ./files ./
RUN yarn install

LABEL IMAGE="project-listing-ui"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"

RUN yarn build

FROM nginx:1.25.4-alpine

RUN mkdir /app
COPY --from=build-stage /app/dist /app
COPY --from=build-stage /app/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]