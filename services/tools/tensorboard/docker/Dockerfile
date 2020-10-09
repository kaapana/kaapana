FROM python:3.9-alpine3.12

LABEL IMAGE="tensorboard"
LABEL VERSION="1.0-vdev"
LABEL CI_IGNORE="False"


RUN pip3 install tensorboard

COPY files/tensorboard.sh /

ENV INGRESS_PATH /tensorboard
ENV LOG_DIR=/data

CMD ["/bin/bash", "/tensorboard.sh"]