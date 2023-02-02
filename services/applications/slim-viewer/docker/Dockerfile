FROM node:lts-alpine as build

LABEL IMAGE="slim"
LABEL VERSION="0.12.0"
LABEL CI_IGNORE="False"

RUN apk add --no-cache ca-certificates git build-base
RUN git clone -c advice.detachedHead=False --depth 1 --branch v0.12.0 https://github.com/MGHComputationalPathology/slim.git /src
WORKDIR /src

COPY local.js public/config/
ARG REACT_APP_CONFIG=local
ARG PUBLIC_URL="/slim"

RUN yarn install --frozen-lockfile --network-timeout 100000
RUN NODE_OPTIONS=--max_old_space_size=8192 yarn run build 

FROM nginx:stable-alpine as app
COPY --from=build /src/build/ /usr/share/nginx/html/slim/

#COPY conf /etc/nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]