FROM python:3.9-slim

LABEL IMAGE="tensorboard"
LABEL VERSION="2.5.0"
LABEL CI_IGNORE="False"

RUN python -m pip install --upgrade pip && pip3 install --no-cache-dir tensorboard==2.5.0

COPY files/tensorboard.sh /

ENV INGRESS_PATH /tensorboard
ENV LOG_DIR=/data

CMD ["/bin/sh", "/tensorboard.sh"]