FROM docker.io/opensearchproject/opensearch:3.7.0

LABEL IMAGE="opensearch"
LABEL VERSION="3.7.0"
LABEL BUILD_IGNORE="False"

USER root
RUN dnf upgrade curl-minimal libcurl-minimal ncurses-base ncurses-libs openssl-libs python3-pip-wheel sqlite-libs glibc glibc-common glibc-minimal-langpack gnupg2-minimal libcap libnghttp2 libsolv python3 python3-libs --security --assumeyes --releasever=latest

COPY /files/start.sh .
COPY /files/init-security.sh .

RUN chmod 777 init-security.sh

USER opensearch

CMD ["/bin/bash", "start.sh"]