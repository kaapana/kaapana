FROM local-only/base-ui:latest AS base-ui

FROM docker.io/node:lts-alpine3.23 AS build-stage

WORKDIR /kaapana/services/applications/collabora/docker/wopi/files/ui
COPY --from=base-ui /kaapana/base-ui/docker/files/package.json /kaapana/services/base/base-ui/docker/files/package.json
COPY --from=base-ui /kaapana/base-ui/docker/files/dist /kaapana/services/base/base-ui/docker/files/dist
COPY files/ui/package*.json ./
RUN npm install -g npm@11.16.0 && npm ci
COPY files/ui .
RUN npm run build


FROM local-only/base-python-cpu:latest

LABEL IMAGE="kaapana-wopi"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY --from=build-stage /kaapana/services/applications/collabora/docker/wopi/files/ui/dist /app/ui/dist
WORKDIR /app

COPY files/requirements.txt /app/
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN python -m pip install -c /constraints.txt --no-cache-dir -r /app/requirements.txt

COPY files/run.sh /app
COPY files/app /app/app

ENTRYPOINT ["/app/run.sh"]