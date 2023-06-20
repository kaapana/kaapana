FROM docker.io/node:20-alpine3.16 as build

LABEL IMAGE="ohif-v3"
LABEL VERSION="v3-stable"
LABEL CI_IGNORE="False"

RUN apk add --no-cache ca-certificates git build-base python3

RUN git clone https://github.com/OHIF/Viewers.git /src && cd /src && git checkout 72ec0bffb533f883aac3b76d0ed9559c70fe5838

RUN yarn config set workspaces-experimental true

WORKDIR /src
RUN git checkout v3-stable

COPY files/viewer-only.patch /src/
RUN git apply viewer-only.patch

COPY files/kaapana.js /src/platform/viewer/public/config/kaapana.js

ENV HTML_TEMPLATE "index.html"
ENV PUBLIC_URL "/ohif-v3/"
ENV APP_CONFIG "config/kaapana.js"

RUN yarn install
RUN yarn run build

FROM docker.io/nginx:stable-alpine as production-stage

COPY --from=build /src/platform/viewer/dist/ /usr/share/nginx/html/ohif-v3/

COPY files/ /usr/share/nginx/html/
COPY files/kaapana.js /usr/share/nginx/html/ohif-v3/app-config.js

COPY conf /etc/nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


