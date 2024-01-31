FROM docker.io/dcm4che/postgres-dcm4chee:15.4-31

LABEL IMAGE="dcm4che-postgres"
LABEL VERSION="9.6.24-26"
LABEL CI_IGNORE="False"
RUN apt-get update 
RUN apt-get upgrade -y
RUN apt-get upgrade postgresql-15 -y
RUN apt upgrade golang-github-containerd-go-runc-dev/stable -y
