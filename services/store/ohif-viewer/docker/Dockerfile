FROM node:lts-alpine as build

LABEL IMAGE="ohif"
LABEL VERSION="4.9.7-vdev"
LABEL CI_IGNORE="False"

RUN apk add --no-cache ca-certificates git build-base python
RUN git clone https://github.com/OHIF/Viewers.git /src

RUN yarn config set workspaces-experimental true

WORKDIR /src
RUN git checkout @ohif/viewer@4.9.7

COPY files/kaapana.js /src/platform/viewer/public/config/kaapana.js

ENV HTML_TEMPLATE "index.html"
ENV PUBLIC_URL "/ohif/"
ENV APP_CONFIG "config/kaapana.js"

RUN yarn install
# --------------------- WORKAROUND ---------------------
# https://github.com/OHIF/Viewers/issues/2138 only tested with @ohif/viewer@4.9.7
COPY files/dcmjs-natural-ds.patch /src/dcmjs-natural-ds.patch
RUN patch -u node_modules/dcmjs/build/dcmjs.es.js -i dcmjs-natural-ds.patch
# --------------------- WORKAROUND END ---------------------
RUN yarn run build


FROM nginx:stable-alpine as production-stage

COPY --from=build /src/platform/viewer/dist/ /usr/share/nginx/html/ohif/

COPY files/ /usr/share/nginx/html/
COPY files/kaapana.js /usr/share/nginx/html/ohif/app-config.js

COPY conf /etc/nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


