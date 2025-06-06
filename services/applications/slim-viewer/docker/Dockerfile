FROM node:lts-alpine AS build

LABEL IMAGE="slim"
LABEL VERSION="0.35.0"
LABEL BUILD_IGNORE="False"

RUN apk add --no-cache ca-certificates git build-base
RUN git clone -c advice.detachedHead=False --depth 1 --branch v0.35.0 https://github.com/MGHComputationalPathology/slim.git /src
WORKDIR /src

COPY local.js public/config/
ARG REACT_APP_CONFIG=local
ARG PUBLIC_URL="/slim"

RUN yarn install --frozen-lockfile --network-timeout 100000
RUN NODE_OPTIONS=--max_old_space_size=8192 yarn run build 

FROM nginx:stable-alpine AS app
COPY --from=build /src/build/ /usr/share/nginx/html/slim/


COPY files/conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
