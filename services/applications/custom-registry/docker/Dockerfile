FROM alpine:3.12

LABEL IMAGE="check-registry-access"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"


RUN apk add --no-cache curl

COPY check-registry.sh /usr/local/bin/check-registry.sh
RUN chmod +x /usr/local/bin/check-registry.sh

ENTRYPOINT ["/usr/local/bin/check-registry.sh"]
