FROM quay.io/oauth2-proxy/oauth2-proxy-nightly:20250513-alpine
LABEL IMAGE="oauth2-proxy"
LABEL VERSION="7.9.0"
LABEL BUILD_IGNORE="False"

COPY files/403.html /usr/share/oauth2-proxy/error.html
USER 0
RUN apk upgrade libssl3 libcrypto3
### user id of the original user in this image
USER 65532
