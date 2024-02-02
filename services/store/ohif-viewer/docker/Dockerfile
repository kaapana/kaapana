FROM docker.io/node:20-alpine3.18 as build

LABEL IMAGE="ohif"
<<<<<<< HEAD
LABEL VERSION="4.12.26"
LABEL BUILD_IGNORE="False"
=======
LABEL VERSION="v3.7.0"
LABEL CI_IGNORE="False"
>>>>>>> 3fd3650c (ohif 3.7.0 as default ohif, v2 backup: /ohif-v2)

RUN apk add --no-cache ca-certificates git build-base python3


RUN git clone https://github.com/OHIF/Viewers.git /src && cd /src && git checkout df32a05a4d64878c3aaccb54c4b19665ffa58788

RUN yarn config set workspaces-experimental true

WORKDIR /src

COPY files/kaapana.js /src/platform/app/public/config/kaapana.js

ENV HTML_TEMPLATE "index.html"
ENV PUBLIC_URL "/ohif/"
ENV APP_CONFIG "config/kaapana.js"

RUN yarn install
RUN yarn run build

FROM docker.io/nginx:1.24.0-alpine@sha256:0ec1c862eb0bca5cce922ea40fe9f6f08361b4e57d9376b3a6c0db622735cc5e as production-stage

COPY --from=build /src/platform/app/dist/ /usr/share/nginx/html/ohif/

COPY files/ /usr/share/nginx/html/
COPY files/kaapana.js /usr/share/nginx/html/ohif/app-config.js

COPY conf /etc/nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


