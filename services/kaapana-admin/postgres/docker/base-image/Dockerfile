FROM golang:alpine AS gosu-builder
RUN go install github.com/tianon/gosu@latest

FROM docker.io/postgres:18.4-alpine

LABEL REGISTRY="local-only"
LABEL IMAGE="postgres-base"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

COPY --from=gosu-builder /go/bin/gosu /usr/local/bin/gosu
RUN apk update && apk upgrade libxml2 musl