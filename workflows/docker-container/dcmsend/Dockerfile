FROM ubuntu:20.04

LABEL IMAGE="dcmsend"
LABEL VERSION="1.0-vdev"
LABEL CI_IGNORE="False"

RUN apt-get update -y && apt-get install -y \
        dcmtk \
    && apt-get clean

COPY files/run.sh .

CMD ["/bin/bash", "/run.sh"]