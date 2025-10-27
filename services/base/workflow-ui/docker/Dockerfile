FROM node:lts-alpine3.19 AS base
LABEL IMAGE="workflow-ui"
LABEL BUILD_IGNORE="False"

WORKDIR /app

COPY ./files/package*.json ./
RUN npm ci --no-audit --prefer-offline

COPY ./files .

################################
######### Development ##########
################################
FROM node:lts-alpine3.19 AS dev

WORKDIR /app

COPY --from=base --chown=1000:1000 /app /app

USER 1000
EXPOSE 5173
CMD ["npm", "run", "serve"]

