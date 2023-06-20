FROM alpine:3.16.2

LABEL REGISTRY="local-only"
LABEL IMAGE="security-pages-frontend"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

RUN apk update && apk add --no-cache npm \
    && rm -rf /var/cache/apk/*

COPY files/ ./
RUN npm install && npm run build
