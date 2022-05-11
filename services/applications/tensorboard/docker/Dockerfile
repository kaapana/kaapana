FROM local-only/base-python-alpine:0.1.0
LABEL IMAGE="tensorboard"
LABEL VERSION="2.8.0"
LABEL CI_IGNORE="False"

RUN pip3 install --no-cache-dir tensorboard==2.8.0

COPY files/tensorboard.sh /

ENV INGRESS_PATH /tensorboard
ENV LOG_DIR=/data

CMD ["/bin/sh", "/tensorboard.sh"]