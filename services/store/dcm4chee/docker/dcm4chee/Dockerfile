FROM docker.io/dcm4che/dcm4chee-arc-psql:5.31.3-secure

LABEL IMAGE="dcm4chee-arc"
LABEL VERSION="5.26.0"
LABEL CI_IGNORE="False"

RUN apt update && apt upgrade -y binutils binutils-common binutils-x86-64-linux-gnu curl libbinutils libc-bin libc6 libctf-nobfd0 libctf0 libcurl4 libgnutls30 libpam-modules libpam-modules-bin libpam-runtime libpam0g libsqlite3-0 libssh-4 libssh-gcrypt-4 locales tar

# COPY files/dcm4chee-arc.xml /docker-entrypoint.d/configuration/dcm4chee-arc.xml