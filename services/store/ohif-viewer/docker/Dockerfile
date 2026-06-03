FROM docker.io/node:26-alpine3.23 AS build

LABEL IMAGE="ohif"
LABEL VERSION="v3.10.1"
LABEL BUILD_IGNORE="False"

RUN apk add --no-cache ca-certificates git build-base python3

RUN npm install -g yarn

RUN git clone https://github.com/OHIF/Viewers.git /src && cd /src && git checkout 9a4a40468fc61e8c4818ea57905239bdff47f634

RUN yarn config set workspaces-experimental true

WORKDIR /src

COPY files/kaapana.js /src/platform/app/public/config/kaapana.js

ENV HTML_TEMPLATE="index.html"
ENV PUBLIC_URL="/ohif/"
ENV APP_CONFIG="config/kaapana.js"

COPY files/customization.patch /src/
RUN git apply --ignore-whitespace customization.patch

RUN yarn install
RUN yarn run build

FROM docker.io/nginx:1.31-alpine AS production-stage

RUN apk update && apk upgrade libxml2

COPY --from=build /src/platform/app/dist/ /usr/share/nginx/html/ohif/

COPY files/ /usr/share/nginx/html/
COPY files/kaapana.js /usr/share/nginx/html/ohif/app-config.js

COPY conf /etc/nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


