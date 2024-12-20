FROM docker.io/opensearchproject/opensearch:2.18.0

LABEL IMAGE="opensearch"
LABEL VERSION="2.18.0"
LABEL BUILD_IGNORE="False"

USER root
RUN dnf upgrade curl-minimal libcurl-minimal ncurses-base ncurses-libs openssl-libs python3-pip-wheel sqlite-libs --security --assumeyes --releasever=latest

COPY /files/start.sh .
COPY /files/init-security.sh .
COPY /files/backup-security.sh .

RUN chmod 777 init-security.sh backup-security.sh

USER opensearch

CMD ["/bin/bash", "start.sh"]