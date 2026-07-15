FROM docker.io/alpine:3.24.1

LABEL IMAGE="node-exporter-textfile-collector"
LABEL BUILD_IGNORE="False"

RUN apk add --no-cache coreutils

COPY collect.sh /collect.sh
RUN chmod +x /collect.sh

ENTRYPOINT ["/collect.sh"]