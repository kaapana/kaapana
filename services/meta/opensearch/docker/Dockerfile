FROM docker.io/opensearchproject/opensearch:2.12.0

LABEL IMAGE="opensearch"
LABEL VERSION="2.12.0"
LABEL BUILD_IGNORE="False"

USER root
RUN dnf upgrade curl-minimal libcurl-minimal ncurses-base ncurses-libs openssl-libs python3-pip-wheel sqlite-libs --security --assumeyes --releasever=latest
USER opensearch

