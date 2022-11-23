FROM alpine:3.12

LABEL IMAGE="cert-init"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="False"

RUN apk add --no-cache kubectl --repository=http://dl-cdn.alpinelinux.org/alpine/edge/testing
RUN apk add --no-cache openssl bash

WORKDIR /cert
COPY handle-secret.sh .
RUN chmod +x handle-secret.sh
CMD ["./handle-secret.sh"]
