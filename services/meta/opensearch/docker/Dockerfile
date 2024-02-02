FROM docker.io/opensearchproject/opensearch:2.11.1

LABEL IMAGE="opensearch"
LABEL VERSION="2.11.1"
LABEL CI_IGNORE="False"

USER root
RUN dnf upgrade curl-minimal libcurl-minimal ncurses-base ncurses-libs openssl-libs python3-pip-wheel sqlite-libs --security --assumeyes --releasever=latest
USER opensearch

