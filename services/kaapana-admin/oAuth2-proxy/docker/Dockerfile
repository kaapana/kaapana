FROM golang:1.26.3-alpine3.23 AS builder
ARG OAUTH2_PROXY_VERSION=v7.15.2
RUN apk add --no-cache git make && \
    git clone --depth 1 --branch ${OAUTH2_PROXY_VERSION} \
      https://github.com/oauth2-proxy/oauth2-proxy.git /src
WORKDIR /src
RUN make build

FROM alpine:3.23
LABEL IMAGE="oauth2-proxy"
LABEL VERSION="7.15.2"
LABEL BUILD_IGNORE="False"

COPY --from=builder /src/oauth2-proxy /bin/oauth2-proxy
COPY files/403.html /usr/share/oauth2-proxy/error.html

RUN addgroup -S -g 65532 nonroot && adduser -S -u 65532 -G nonroot nonroot
USER 65532
ENTRYPOINT ["/bin/oauth2-proxy"]