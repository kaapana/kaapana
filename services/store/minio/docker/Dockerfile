FROM golang:1.14-alpine as builder


LABEL maintainer="MinIO Inc <dev@min.io>"

ENV GOPATH /go
ENV CGO_ENABLED 0
ENV GO111MODULE on

# Checking out verison RELEASE.2020-09-17T04-49-20Z
RUN  \
     apk add --no-cache git && \
     git clone https://github.com/minio/minio && cd minio && \
     git checkout ed78854cead490ca6de6fe2e3255d000519a65e4

WORKDIR /go/minio

COPY web-handlers.go /go/minio/cmd/
COPY jwt.go /go/minio/cmd/config/identity/openid/

RUN go install -v -ldflags "$(go run buildscripts/gen-ldflags.go)"

FROM alpine:3.12


LABEL IMAGE=minio
LABEL VERSION=2020.09.17-vdev
LABEL CI_IGNORE=False


ENV MINIO_UPDATE off
ENV MINIO_ACCESS_KEY_FILE=access_key \
    MINIO_SECRET_KEY_FILE=secret_key \
    MINIO_KMS_MASTER_KEY_FILE=kms_master_key \
    MINIO_SSE_MASTER_KEY_FILE=sse_master_key

EXPOSE 9000

COPY --from=builder /go/bin/minio /usr/bin/minio
COPY --from=builder /go/minio/CREDITS /third_party/
COPY --from=builder /go/minio/dockerscripts/docker-entrypoint.sh /usr/bin/

RUN  \
     apk add --no-cache ca-certificates 'curl>7.61.0' 'su-exec>=0.2' && \
     echo 'hosts: files mdns4_minimal [NOTFOUND=return] dns mdns4' >> /etc/nsswitch.conf

ENTRYPOINT ["/usr/bin/docker-entrypoint.sh"]

VOLUME ["/data"]

CMD ["minio"]