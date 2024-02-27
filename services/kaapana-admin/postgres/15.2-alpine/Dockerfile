FROM docker.io/postgres:15.2-alpine

LABEL IMAGE="postgres-15.2-alpine"
LABEL VERSION="15.2-alpine"
LABEL BUILD_IGNORE="False"

RUN apk update && apk upgrade libssl3 libcrypto3 libxml2 ncurses-libs ncurses-terminfo-base
