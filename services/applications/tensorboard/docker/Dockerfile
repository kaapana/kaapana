FROM python:3.9-alpine3.12

LABEL IMAGE="tensorboard"
LABEL VERSION="2.4.1"
LABEL CI_IGNORE="False"

RUN apk add --no-cache build-base linux-headers

RUN python -m pip install --upgrade pip && pip3 install --no-cache-dir tensorboard==2.4.1

COPY files/tensorboard.sh /

ENV INGRESS_PATH /tensorboard
ENV LOG_DIR=/data

CMD ["/bin/sh", "/tensorboard.sh"]