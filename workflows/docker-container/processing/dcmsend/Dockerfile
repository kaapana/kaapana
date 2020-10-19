FROM ubuntu:20.04

LABEL IMAGE="dcmsend"
LABEL VERSION="3.6.2"
LABEL CI_IGNORE="False"

RUN apt-get update -y && apt-get install -y \
        dcmtk \
    && apt-get clean

COPY files/run.sh .

CMD ["/bin/bash", "/run.sh"]