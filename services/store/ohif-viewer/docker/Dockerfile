FROM node:lts-alpine3.10 as build

LABEL IMAGE="ohif"
LABEL VERSION="4.12.25"
LABEL CI_IGNORE="False"

RUN apk add --no-cache ca-certificates git build-base python
RUN git clone https://github.com/OHIF/Viewers.git /src

RUN yarn config set workspaces-experimental true

WORKDIR /src
RUN git checkout @ohif/viewer@4.12.25

COPY files/kaapana.js /src/platform/viewer/public/config/kaapana.js

ENV HTML_TEMPLATE "index.html"
ENV PUBLIC_URL "/ohif/"
ENV APP_CONFIG "config/kaapana.js"

RUN yarn install
# Adapated by Kaapana basically reversing this change: https://github.com/OHIF/Viewers/issues/2345#issuecomment-821910646
RUN yarn add --peer -W dcmjs@0.18.4
RUN yarn run build

FROM nginx:stable-alpine as production-stage

COPY --from=build /src/platform/viewer/dist/ /usr/share/nginx/html/ohif/

COPY files/ /usr/share/nginx/html/
COPY files/kaapana.js /usr/share/nginx/html/ohif/app-config.js

COPY conf /etc/nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


