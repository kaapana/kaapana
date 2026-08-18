FROM docker.io/node:lts-alpine3.16 as build-stage

WORKDIR /app
COPY files/ui/package*.json ./
RUN npm install -g npm@9.9.4 && npm ci

COPY files/ui .
RUN npm run build


FROM local-only/base-python-cpu:latest

LABEL IMAGE="kaapana-wopi"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY --from=build-stage /app/dist /app/ui/dist
WORKDIR /app

COPY files/requirements.txt /app/
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN python -m pip install -c /constraints.txt --no-cache-dir -r /app/requirements.txt

COPY files/run.sh /app
COPY files/app /app/app

ENTRYPOINT ["/app/run.sh"]