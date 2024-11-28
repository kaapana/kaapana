FROM docker.io/node:23-alpine3.20 as build

LABEL IMAGE="ohif"
LABEL VERSION="v3.9.1"
LABEL BUILD_IGNORE="False"

RUN apk add --no-cache ca-certificates git build-base python3


RUN git clone https://github.com/OHIF/Viewers.git /src && cd /src && git checkout 3b668675084bc7bb506f1d960d98e9563e6d4899

RUN yarn config set workspaces-experimental true

WORKDIR /src

COPY files/kaapana.js /src/platform/app/public/config/kaapana.js

ENV HTML_TEMPLATE "index.html"
ENV PUBLIC_URL "/ohif/"
ENV APP_CONFIG "config/kaapana.js"

RUN yarn install
RUN yarn run build

FROM docker.io/nginx:1.27.3-alpine as production-stage

COPY --from=build /src/platform/app/dist/ /usr/share/nginx/html/ohif/

COPY files/ /usr/share/nginx/html/
COPY files/kaapana.js /usr/share/nginx/html/ohif/app-config.js

COPY conf /etc/nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


