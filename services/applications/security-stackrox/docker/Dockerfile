FROM alpine/git:latest as build-stage

LABEL IMAGE="security-stackrox-build"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="False"

WORKDIR /
RUN git clone -b 3.72.1 https://github.com/stackrox/stackrox.git -c advice.detachedHead=false

FROM ubuntu:jammy

LABEL IMAGE="security-stackrox"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="False"

COPY --from=build-stage /stackrox/ /stackrox/

RUN apt update && apt install -y git make

COPY files/ ./
RUN chmod +x init.sh

ENTRYPOINT ["/init.sh"]
