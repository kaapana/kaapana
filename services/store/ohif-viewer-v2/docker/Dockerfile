FROM docker.io/node:lts-alpine3.10 as build

LABEL IMAGE="ohif-v2"
LABEL VERSION="4.12.26"
LABEL CI_IGNORE="False"

RUN apk add --no-cache ca-certificates git build-base python
RUN git clone https://github.com/OHIF/Viewers.git /src

RUN yarn config set workspaces-experimental true

WORKDIR /src
RUN git checkout @ohif/viewer@4.12.26

COPY files/getModalities.patch /src/
RUN git apply getModalities.patch

COPY files/kaapana.js /src/platform/viewer/public/config/kaapana.js

ENV HTML_TEMPLATE "index.html"
ENV PUBLIC_URL "/ohif/"
ENV APP_CONFIG "config/kaapana.js"

RUN yarn install
RUN yarn run build

FROM docker.io/nginx:1.24.0-alpine@sha256:0ec1c862eb0bca5cce922ea40fe9f6f08361b4e57d9376b3a6c0db622735cc5e as production-stage

COPY --from=build /src/platform/viewer/dist/ /usr/share/nginx/html/ohif-v2/

COPY files/ /usr/share/nginx/html/
COPY files/kaapana.js /usr/share/nginx/html/ohif-v2/app-config.js

COPY conf /etc/nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


