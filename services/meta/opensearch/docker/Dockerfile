FROM docker.io/opensearchproject/opensearch:2.11.1

LABEL IMAGE="opensearch"
LABEL VERSION="2.11.1"
LABEL CI_IGNORE="False"

USER root
RUN dnf upgrade --security --assumeyes --releasever=latest
USER opensearch
# COPY files/commons-compress-1.24.0.jar 

# RUN yum upgrade -y 
# RUN yum install -y curl-minimal libcurl-minimal ncurses-base openssl-libs python3-pip-wheel sqlite-libs

# USER opensearch
