FROM docker.io/alpine:3.17.7 as builder

RUN apk add --no-cache openssl bash jq curl
COPY files/generate-certificates.sh .
RUN /bin/bash generate-certificates.sh

FROM docker.io/opensearchproject/opensearch:2.12.0

LABEL IMAGE="opensearch"
LABEL VERSION="2.12.0"
LABEL BUILD_IGNORE="False"

USER root
RUN dnf upgrade curl-minimal libcurl-minimal ncurses-base ncurses-libs openssl-libs python3-pip-wheel sqlite-libs --security --assumeyes --releasever=latest
COPY --from=builder root-ca.pem /usr/share/opensearch/config/
COPY --from=builder admin.pem /usr/share/opensearch/config/
COPY --from=builder admin-key.pem /usr/share/opensearch/config/
COPY --from=builder node1.pem /usr/share/opensearch/config/
COPY --from=builder node1-key.pem /usr/share/opensearch/config/

RUN chown 1000:1000 -R /usr/share/opensearch/config/

USER opensearch