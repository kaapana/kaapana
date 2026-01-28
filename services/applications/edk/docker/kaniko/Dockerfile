# simplified version of Kaniko executor from Chainguard's maintained fork

FROM golang:1.23-alpine AS builder

WORKDIR /src

RUN apk add --no-cache git make bash

# clone the fork
RUN git clone https://github.com/chainguard-dev/kaniko.git . && \
    git checkout main

# download Go toolchain
ENV GOTOOLCHAIN=auto
ENV CGO_ENABLED=0

# build executor
RUN --mount=type=cache,target=/root/.cache/go-build \
    --mount=type=cache,target=/go/pkg \
    make out/executor

# generate CA certificates
FROM debian:bookworm-slim AS certs
RUN apt update && apt install -y ca-certificates

# final image, build from distroless so it has minimal attack surface
FROM gcr.io/distroless/static-debian12@sha256:cd64bec9cec257044ce3a8dd3620cf83b387920100332f2b041f19c4d2febf93

LABEL IMAGE="kaniko-executor"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

# copy certs
COPY --from=certs /etc/ssl/certs/ca-certificates.crt /kaniko/ssl/certs/

# copy nsswitch.conf from the repo
COPY --from=builder /src/files/nsswitch.conf /etc/nsswitch.conf

# copy the executor binary
COPY --from=builder /src/out/executor /kaniko/executor

# set env vars
ENV HOME=/root \
    USER=root \
    PATH=/kaniko:/usr/local/bin \
    SSL_CERT_DIR=/kaniko/ssl/certs \
    DOCKER_CONFIG=/kaniko/.docker/

WORKDIR /workspace

ENTRYPOINT ["/kaniko/executor"]
