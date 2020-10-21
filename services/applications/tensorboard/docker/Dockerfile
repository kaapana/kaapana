FROM python:3

LABEL IMAGE="tensorboard"
LABEL VERSION="2.3.0"
LABEL CI_IGNORE="False"

RUN pip3 install tensorboard==2.3.0

COPY files/tensorboard.sh /

ENV INGRESS_PATH /tensorboard
ENV LOG_DIR=/data

CMD ["/bin/bash", "/tensorboard.sh"]