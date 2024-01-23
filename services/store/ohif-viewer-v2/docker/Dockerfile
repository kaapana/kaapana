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

FROM docker.io/nginx:1.24.0-alpine as production-stage

## Security fix for CVE-2023-6129
RUN apk update && \
    apk upgrade && \
    apk add libssl3==3.0.12-r3 libcrypto3==3.0.12-r3

COPY --from=build /src/platform/viewer/dist/ /usr/share/nginx/html/ohif-v2/

COPY files/ /usr/share/nginx/html/
COPY files/kaapana.js /usr/share/nginx/html/ohif-v2/app-config.js

COPY conf /etc/nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


