FROM docker.io/node:20-alpine3.18 as build

LABEL IMAGE="ohififrame"
LABEL VERSION="v3.7.0"
LABEL BUILD_IGNORE="False"


RUN apk add --no-cache ca-certificates git build-base python3
RUN git clone https://github.com/OHIF/Viewers.git /src && cd /src && git checkout 72ec0bffb533f883aac3b76d0ed9559c70fe5838

RUN yarn config set workspaces-experimental true

WORKDIR /src


COPY files/viewer-only.patch /src/
RUN git apply viewer-only.patch

COPY files/bugfix.patch /src/
RUN git apply bugfix.patch

COPY files/load-segmetation.patch /src/
RUN git apply load-segmetation.patch

COPY files/kaapana.js /src/platform/app/public/config/kaapana.js

ENV HTML_TEMPLATE "index.html"
ENV PUBLIC_URL "/ohif-iframe/"
ENV APP_CONFIG "config/kaapana.js"

RUN yarn install
RUN yarn run build

FROM docker.io/nginx:1.25.4-alpine as production-stage


COPY --from=build /src/platform/app/dist/ /usr/share/nginx/html/ohif-iframe/

COPY files/ /usr/share/nginx/html/
COPY files/kaapana.js /usr/share/nginx/html/ohif-iframe/app-config.js

COPY conf /etc/nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


