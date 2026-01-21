FROM docker.io/alpine:3.19

LABEL IMAGE="node-exporter-textfile-collector"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"

RUN apk add --no-cache coreutils

COPY collect.sh /collect.sh
RUN chmod +x /collect.sh

ENTRYPOINT ["/collect.sh"]